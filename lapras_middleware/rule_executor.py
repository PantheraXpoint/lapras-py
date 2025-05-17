import logging
import time
import json
import threading
from typing import Dict, Any, List
import paho.mqtt.client as mqtt
import rdflib
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD

logger = logging.getLogger(__name__)

class RuleExecutor:
    """Rule executor that processes context states and applies rules."""
    
    def __init__(self, mqtt_broker: str = "localhost", mqtt_port: int = 1883):
        """Initialize the rule executor."""
        # Set up MQTT client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.connect(mqtt_broker, mqtt_port)
        
        # Initialize RDF graph for rules
        self.rules_graph = Graph()
        self.namespace = Namespace("http://lapras.org/rule/")
        self.rules_graph.bind("lapras", self.namespace)
        
        # Start MQTT client loop
        self.mqtt_client.loop_start()
        logger.info("[RULE_EXECUTOR] Rule executor initialized")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        logger.info(f"[RULE_EXECUTOR] Connected to MQTT broker with result code {rc}")
        # Subscribe to rule executor channel
        self.mqtt_client.subscribe("to_rule_executor")
    
    def _on_message(self, client, userdata, msg):
        """Callback when message is received from MQTT broker."""
        try:
            data = json.loads(msg.payload.decode())
            context_map = data.get("context_map", {})
            timestamp = data.get("timestamp")
            
            if context_map:
                logger.info(f"[RULE_EXECUTOR] Received context map with {len(context_map)} agents")
                # Process each agent's state
                for agent_id, agent_state in context_map.items():
                    logger.info(f"[RULE_EXECUTOR] Processing rules for agent {agent_id}")
                    logger.info(f"[RULE_EXECUTOR] Current state: {json.dumps(agent_state, indent=2)}")
                    
                    # Evaluate rules for this agent
                    new_state = self.evaluate_rules(agent_id, agent_state)
                    if new_state:
                        # Publish new state to context distribution
                        message = {
                            "agent_id": agent_id,
                            "state": new_state,
                            "timestamp": timestamp
                        }
                        self.mqtt_client.publish("context_dist", json.dumps(message))
                        logger.info(f"[RULE_EXECUTOR] Published new state for agent {agent_id}: {json.dumps(new_state, indent=2)}")
                    else:
                        logger.info(f"[RULE_EXECUTOR] No rules triggered for agent {agent_id}")
            else:
                logger.info("[RULE_EXECUTOR] Received empty context map")
        except Exception as e:
            logger.error(f"[RULE_EXECUTOR] Error processing message: {e}")
    
    def evaluate_rules(self, agent_id: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate rules for an agent and return new state if rules match."""
        try:
            # Query for rules specific to this agent
            rules_query = """
            SELECT ?rule ?condition ?action
            WHERE {
                ?rule rdf:type lapras:Rule .
                ?rule lapras:hasAgent ?agent .
                ?rule lapras:hasCondition ?condition .
                ?rule lapras:hasAction ?action .
                FILTER(?agent = ?agent_id)
            }
            """
            
            new_state = current_state.copy()
            rules_matched = False
            
            for rule, condition, action in self.rules_graph.query(rules_query, initBindings={'agent_id': Literal(agent_id)}):
                rule_name = str(rule).split('#')[-1]
                logger.info(f"[RULE_EXECUTOR] Evaluating rule {rule_name} for agent {agent_id}")
                
                # Get condition details for logging
                condition_query = """
                SELECT ?sensor ?operator ?value
                WHERE {
                    ?condition lapras:hasSensor ?sensor .
                    ?condition lapras:hasOperator ?operator .
                    ?condition lapras:hasValue ?value .
                }
                """
                for sensor, operator, value in self.rules_graph.query(condition_query, initBindings={'condition': condition}):
                    sensor_id = str(sensor)
                    operator_str = str(operator).split('/')[-1]  # Extract just the operator name from URI
                    threshold_value = float(value)
                    current_value = current_state.get(sensor_id)
                    
                    logger.info(f"[RULE_EXECUTOR] Condition check: {sensor_id} {operator_str} {threshold_value}")
                    logger.info(f"[RULE_EXECUTOR] Current value: {current_value}, Current action: {self._parse_action(action)}")
                
                if self._evaluate_condition(condition, current_state):
                    action_data = self._parse_action(action)
                    if action_data:
                        logger.info(f"[RULE_EXECUTOR] Rule {rule_name} TRIGGERED")
                        logger.info(f"[RULE_EXECUTOR] Action to be applied: {json.dumps(action_data, indent=2)}")
                        # Apply action to state
                        new_state.update(action_data.get("state_update", {}))
                        rules_matched = True
                    else:
                        logger.warning(f"[RULE_EXECUTOR] Rule {rule_name} matched but action parsing failed")
                else:
                    logger.info(f"[RULE_EXECUTOR] Rule {rule_name} condition not met")
            
            if rules_matched:
                logger.info(f"[RULE_EXECUTOR] Final state after rules: {json.dumps(new_state, indent=2)}")
            return new_state if rules_matched else None
            
        except Exception as e:
            logger.error(f"[RULE_EXECUTOR] Error evaluating rules: {e}")
            return None
    
    def _evaluate_condition(self, condition: rdflib.term.Node, state: Dict[str, Any]) -> bool:
        """Evaluate a single condition against state."""
        try:
            # Query for condition details
            condition_query = """
            SELECT ?sensor ?operator ?value
            WHERE {
                ?condition lapras:hasSensor ?sensor .
                ?condition lapras:hasOperator ?operator .
                ?condition lapras:hasValue ?value .
            }
            """
            
            logger.info(f"[RULE_EXECUTOR] Evaluating condition: {condition}")
            logger.info(f"[RULE_EXECUTOR] Current state: {json.dumps(state, indent=2)}")
            
            for sensor, operator, value in self.rules_graph.query(condition_query, initBindings={'condition': condition}):
                sensor_id = str(sensor)
                operator_str = str(operator).split('/')[-1]  # Extract just the operator name from URI
                threshold_value = float(value)
                
                logger.info(f"[RULE_EXECUTOR] Condition details:")
                logger.info(f"  Sensor: {sensor_id}")
                logger.info(f"  Operator: {operator_str}")
                logger.info(f"  Threshold: {threshold_value}")
                
                # Get sensor value from state
                sensor_value = state.get(sensor_id)
                if sensor_value is None:
                    logger.info(f"[RULE_EXECUTOR] Sensor {sensor_id} not found in state")
                    return False
                
                try:
                    sensor_value = float(sensor_value)
                except (ValueError, TypeError):
                    logger.warning(f"[RULE_EXECUTOR] Invalid sensor value for {sensor_id}: {sensor_value}")
                    return False
                
                # Evaluate the condition
                result = False
                if operator_str == "greaterThan":
                    result = sensor_value > threshold_value
                elif operator_str == "lessThan":
                    result = sensor_value < threshold_value
                elif operator_str == "greaterThanOrEqual":
                    result = sensor_value >= threshold_value
                elif operator_str == "lessThanOrEqual":
                    result = sensor_value <= threshold_value
                elif operator_str == "equals":
                    result = sensor_value == threshold_value
                
                logger.info(f"[RULE_EXECUTOR] Condition evaluation: {sensor_value} {operator_str} {threshold_value} = {result}")
                return result
            
            logger.warning("[RULE_EXECUTOR] No condition details found in RDF graph")
            return False
            
        except Exception as e:
            logger.error(f"[RULE_EXECUTOR] Error evaluating condition: {e}")
            return False
    
    def _parse_action(self, action: rdflib.term.Node) -> Dict[str, Any]:
        """Parse an action node into a dictionary."""
        try:
            action_query = """
            SELECT ?state_update
            WHERE {
                ?action lapras:hasStateUpdate ?state_update .
            }
            """
            
            for state_update, in self.rules_graph.query(action_query, initBindings={'action': action}):
                try:
                    return {"state_update": json.loads(str(state_update))}
                except json.JSONDecodeError:
                    logger.error(f"[RULE_EXECUTOR] Invalid state update JSON: {state_update}")
                    return None
                    
            return None
            
        except Exception as e:
            logger.error(f"[RULE_EXECUTOR] Error parsing action: {e}")
            return None
    
    def load_rules(self, rdf_file_path: str) -> None:
        """Load rules from an RDF file."""
        try:
            self.rules_graph.parse(rdf_file_path, format="turtle")
            logger.info(f"[RULE_EXECUTOR] Successfully loaded rules from {rdf_file_path}")
            
            # Log loaded rules by agent
            rules_query = """
            SELECT ?agent ?rule ?condition ?action
            WHERE {
                ?rule rdf:type lapras:Rule .
                ?rule lapras:hasAgent ?agent .
                ?rule lapras:hasCondition ?condition .
                ?rule lapras:hasAction ?action .
            }
            """
            for agent, rule, condition, action in self.rules_graph.query(rules_query):
                rule_name = str(rule).split('#')[-1]
                logger.info(f"[RULE_EXECUTOR] Loaded rule {rule_name} for agent {agent}:")
                logger.info(f"  Condition: {condition}")
                logger.info(f"  Action: {action}")
                
        except Exception as e:
            logger.error(f"[RULE_EXECUTOR] Failed to load rules from {rdf_file_path}: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the rule executor."""
        logger.info("[RULE_EXECUTOR] Stopping rule executor...")
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        logger.info("[RULE_EXECUTOR] Rule executor stopped")

def main():
    """Main function to run the rule executor."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s] - %(message)s'
    )
    
    try:
        # Initialize rule executor
        rule_executor = RuleExecutor()
        
        # Load rules
        rule_executor.load_rules("lapras_middleware/rules/rules.ttl")
        
        logger.info("[RULE_EXECUTOR] Rule executor started and monitoring context updates")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("[RULE_EXECUTOR] Received keyboard interrupt")
    except Exception as e:
        logger.error(f"[RULE_EXECUTOR] Error in rule executor: {e}")
    finally:
        if 'rule_executor' in locals():
            rule_executor.stop()
        logger.info("[RULE_EXECUTOR] Rule executor stopped")

if __name__ == "__main__":
    main() 