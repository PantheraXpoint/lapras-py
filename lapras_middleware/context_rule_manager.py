import logging
import time
import json
import threading
from typing import Dict, Any, Optional

import paho.mqtt.client as mqtt
import rdflib
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD

from .event import EventFactory, MQTTMessage, TopicManager, ContextPayload, ActionReportPayload

logger = logging.getLogger(__name__)

class ContextRuleManager:
    """Combined context manager and rule executor that processes context states and applies rules."""

    def __init__(self, mqtt_broker: str = "143.248.57.73", mqtt_port: int = 1883):
        """Initialize the combined context rule manager."""
        self.service_id = "ContextRuleManager"
        
        # Context management attributes
        self.context_map: Dict[str, Dict[str, Any]] = {}
        self.context_lock = threading.Lock()
        
        # Rule execution attributes
        self.rules_graph = Graph()
        
        # Define lapras namespace for SPARQL queries
        self.lapras = Namespace("http://lapras.org/rule/")
        self.rules_graph.bind("lapras", self.lapras)
        
        # Track known virtual agents for dynamic topic subscription
        self.known_agents: set = set()
        
        # Set up MQTT client with a unique client ID
        mqtt_client_id = f"{self.service_id}-{int(time.time()*1000)}"
        self.mqtt_client = mqtt.Client(client_id=mqtt_client_id)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        
        try:
            self.mqtt_client.connect(mqtt_broker, mqtt_port)
        except Exception as e:
            logger.error(f"[{self.service_id}] MQTT connection error: {e}", exc_info=True)
            raise

        # Start MQTT client loop
        self.mqtt_client.loop_start()
        logger.info(f"[{self.service_id}] Initialized with client ID: {mqtt_client_id} and connected to MQTT broker.")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            logger.info(f"[{self.service_id}] Successfully connected to MQTT broker.")
            # Subscribe to updateContext events from all virtual agents using wildcard
            # Topic pattern: virtual/+/to/context/updateContext
            context_topic_pattern = "virtual/+/to/context/updateContext"
            self.mqtt_client.subscribe(context_topic_pattern)
            logger.info(f"[{self.service_id}] Subscribed to topic pattern: {context_topic_pattern}")
            
            # Subscribe to actionReport events from all virtual agents using wildcard
            # Topic pattern: virtual/+/to/context/actionReport
            report_topic_pattern = "virtual/+/to/context/actionReport"
            self.mqtt_client.subscribe(report_topic_pattern)
            logger.info(f"[{self.service_id}] Subscribed to topic pattern: {report_topic_pattern}")
        else:
            logger.error(f"[{self.service_id}] Failed to connect to MQTT broker. Result code: {rc}")

    def _on_message(self, client, userdata, msg):
        """Callback when message is received from virtual agents."""
        logger.debug(f"[{self.service_id}] Message received on topic '{msg.topic}'")
        try:
            event = MQTTMessage.deserialize(msg.payload.decode())
            
            if event.event.type == "updateContext":
                # Handle updateContext event from VirtualAgent (ASYNCHRONOUS)
                self._handle_context_update(event)
            elif event.event.type == "actionReport":
                # Handle actionReport event from VirtualAgent (SYNCHRONOUS - Response)
                self._handle_action_report(event)
            else:
                logger.warning(f"[{self.service_id}] Unknown event type: {event.event.type}")
                
        except json.JSONDecodeError:
            logger.error(f"[{self.service_id}] Message payload on topic '{msg.topic}' was not valid JSON: {msg.payload.decode(errors='ignore')}")
        except Exception as e:
            logger.error(f"[{self.service_id}] Error processing message: {e}", exc_info=True)

    def _handle_context_update(self, event):
        """Handle updateContext event from VirtualAgent (ASYNCHRONOUS)."""
        try:
            context_payload = MQTTMessage.get_payload_as(event, ContextPayload)
            agent_id = event.source.entityId
            
            # Update context map
            with self.context_lock:
                self.context_map[agent_id] = {
                    "state": context_payload.state,
                    "agent_type": context_payload.agent_type,
                    "sensors": context_payload.sensors,
                    "timestamp": event.event.timestamp,
                    "last_update": time.time()
                }
                logger.info(f"[{self.service_id}] Updated context for agent {agent_id}")
                logger.debug(f"[{self.service_id}] Current context map: {json.dumps(self.context_map, indent=2)}")
            
            # Track this agent for future action commands
            self.known_agents.add(agent_id)
            
            # Immediately apply rules for this agent
            self._apply_rules_for_agent(agent_id, context_payload.state, event.event.timestamp)
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error handling context update: {e}", exc_info=True)

    def _handle_action_report(self, event):
        """Handle actionReport event from VirtualAgent (SYNCHRONOUS - Response)."""
        try:
            report_payload = MQTTMessage.get_payload_as(event, ActionReportPayload)
            agent_id = event.source.entityId
            
            logger.info(f"[{self.service_id}] Received action report from {agent_id}: success={report_payload.success}, message='{report_payload.message}'")
            
            if report_payload.new_state:
                # Update our context map with the new state
                with self.context_lock:
                    if agent_id in self.context_map:
                        self.context_map[agent_id]["state"].update(report_payload.new_state)
                        self.context_map[agent_id]["last_update"] = time.time()
                        logger.info(f"[{self.service_id}] Updated context for {agent_id} with new state from action report")
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error handling action report: {e}", exc_info=True)

    def _apply_rules_for_agent(self, agent_id: str, current_state: Dict[str, Any], timestamp: Any):
        """Apply rules for a specific agent immediately when context is updated."""
        try:
            logger.info(f"[{self.service_id}] Processing rules for agent '{agent_id}'")
            logger.debug(f"[{self.service_id}] State for '{agent_id}': {json.dumps(current_state, indent=2)}")
            
            state_after_rules = self.evaluate_rules(agent_id, current_state)

            if state_after_rules is not None:
                # Only publish if the state actually changed as a result of the rules
                if state_after_rules != current_state:
                    # Determine what actions need to be taken based on state changes
                    actions_to_execute = self._determine_actions_from_state_change(current_state, state_after_rules)
                    
                    for action in actions_to_execute:
                        self._send_action_command(agent_id, action["actionName"], action.get("parameters"))
                    
                    logger.info(f"[{self.service_id}] State for agent '{agent_id}' CHANGED by rules. Sent {len(actions_to_execute)} action commands.")
                else:
                    logger.info(f"[{self.service_id}] Rules evaluated for agent '{agent_id}', but resulting state is IDENTICAL to original. No actions sent.")
            else:
                logger.info(f"[{self.service_id}] No applicable rules resulted in a state change for agent '{agent_id}', or an error occurred in evaluation.")
                
        except Exception as e:
            logger.error(f"[{self.service_id}] Error applying rules for agent '{agent_id}': {e}", exc_info=True)

    def _determine_actions_from_state_change(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> list:
        """Determine what action commands to send based on state changes."""
        actions = []
        
        # Check for power state changes
        if old_state.get("power") != new_state.get("power"):
            if new_state.get("power") == "on":
                actions.append({"actionName": "turn_on"})
            elif new_state.get("power") == "off":
                actions.append({"actionName": "turn_off"})
        
        # Check for temperature changes
        if old_state.get("temperature") != new_state.get("temperature"):
            actions.append({
                "actionName": "set_temperature",
                "parameters": {"temperature": new_state.get("temperature")}
            })
        
        # Check for mode changes
        if old_state.get("mode") != new_state.get("mode"):
            actions.append({
                "actionName": "set_mode", 
                "parameters": {"mode": new_state.get("mode")}
            })
        
        return actions

    def _send_action_command(self, agent_id: str, action_name: str, parameters: Optional[Dict[str, Any]] = None):
        """Send an action command to a VirtualAgent (SYNCHRONOUS - Request)."""
        try:
            # Create applyAction event
            action_event = EventFactory.create_action_event(
                virtual_agent_id=agent_id,
                action_name=action_name,
                parameters=parameters
            )
            
            # Publish to the agent's action topic
            action_topic = TopicManager.context_to_virtual_action(agent_id)
            action_message = MQTTMessage.serialize(action_event)
            self.mqtt_client.publish(action_topic, action_message)
            
            logger.info(f"[{self.service_id}] Sent action command '{action_name}' to agent '{agent_id}' on topic '{action_topic}'")
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error sending action command to {agent_id}: {e}", exc_info=True)

    def evaluate_rules(self, agent_id: str, current_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate rules for a specific agent based on its current state.
        Handles rules with multiple conditions (all conditions for a rule must be ANDed).
        Returns the new state dictionary if any rule successfully applied a state_update, otherwise None.
        """
        try:
            agent_id_rdf_literal = rdflib.Literal(agent_id)
            agent_specific_rules_query = """
            SELECT DISTINCT ?rule_uri ?action_uri
            WHERE {
                ?rule_uri lapras:hasAgent ?agent_id_param .
                ?rule_uri lapras:hasAction ?action_uri .
            }
            """
            new_state_after_all_rules = current_state.copy()
            any_rule_led_to_actionable_change = False
            logger.debug(f"[{self.service_id}] Evaluating rules for agent '{agent_id}' with initial state: {json.dumps(current_state, indent=2)}")

            for rule_uri, action_uri in self.rules_graph.query(
                agent_specific_rules_query,
                initBindings={'agent_id_param': agent_id_rdf_literal}
            ):
                rule_name_short = str(rule_uri).split('/')[-1] or str(rule_uri)
                logger.info(f"[{self.service_id}] Considering rule '{rule_name_short}' (URI: {rule_uri}) for agent '{agent_id}'")

                rule_conditions_query = """
                SELECT ?condition_node
                WHERE { ?current_rule_param lapras:hasCondition ?condition_node . }
                """
                conditions_for_this_rule = list(self.rules_graph.query(
                    rule_conditions_query, initBindings={'current_rule_param': rule_uri}
                ))

                if not conditions_for_this_rule:
                    logger.info(f"[{self.service_id}] Rule '{rule_name_short}' has no 'lapras:hasCondition' predicates. Skipping.")
                    continue

                all_conditions_met_for_this_rule = True
                for i, condition_row in enumerate(conditions_for_this_rule):
                    condition_node = condition_row[0]
                    condition_name_short = str(condition_node).split('/')[-1] or str(condition_node)
                    logger.debug(f"[{self.service_id}]   Checking condition #{i+1} ('{condition_name_short}') for rule '{rule_name_short}'")
                    if not self._evaluate_condition(condition_node, current_state):
                        all_conditions_met_for_this_rule = False
                        logger.info(f"[{self.service_id}]   Condition '{condition_name_short}' for rule '{rule_name_short}' was FALSE. Rule will not trigger.")
                        break

                if all_conditions_met_for_this_rule:
                    logger.info(f"[{self.service_id}] Rule '{rule_name_short}' ALL {len(conditions_for_this_rule)} conditions met for agent '{agent_id}'")
                    action_data = self._parse_action(action_uri)
                    if action_data and "state_update" in action_data:
                        state_update_payload = action_data["state_update"]
                        if isinstance(state_update_payload, dict):
                            # Check if the state update actually changes anything
                            changed_by_this_action = False
                            for key, value in state_update_payload.items():
                                if new_state_after_all_rules.get(key) != value:
                                    changed_by_this_action = True
                                    break
                            
                            if changed_by_this_action:
                                logger.info(f"[{self.service_id}] Action for rule '{rule_name_short}' provides state_update: {json.dumps(state_update_payload, indent=2)}")
                                new_state_after_all_rules.update(state_update_payload)
                                any_rule_led_to_actionable_change = True
                                logger.info(f"[{self.service_id}] Agent '{agent_id}' state after rule '{rule_name_short}': {json.dumps(new_state_after_all_rules, indent=2)}")
                            else:
                                logger.info(f"[{self.service_id}] Action for rule '{rule_name_short}' triggered, but state_update {json.dumps(state_update_payload, indent=2)} does not change current aggregated state for '{agent_id}'.")
                        else:
                            logger.warning(f"[{self.service_id}] Rule '{rule_name_short}' state_update payload is not a dictionary: {state_update_payload}. Action URI: {action_uri}")
                    elif action_data is None:
                        logger.warning(f"[{self.service_id}] Rule '{rule_name_short}' conditions met, but _parse_action returned None. Action URI: {action_uri}")
                    else:
                        logger.warning(f"[{self.service_id}] Rule '{rule_name_short}' conditions met, but parsed action_data missing 'state_update'. Action URI: {action_uri}, Data: {action_data}")

            if any_rule_led_to_actionable_change:
                logger.info(f"[{self.service_id}] Final cumulative state for agent '{agent_id}' after all rules: {json.dumps(new_state_after_all_rules, indent=2)}")
                return new_state_after_all_rules
            else:
                logger.info(f"[{self.service_id}] No rules triggered an actual state_update for agent '{agent_id}'.")
                return None
        except Exception as e:
            logger.error(f"[{self.service_id}] Critical error in evaluate_rules for agent '{agent_id}': {e}", exc_info=True)
            return None

    def _evaluate_condition(self, condition_node: rdflib.term.Node, current_agent_state: Dict[str, Any]) -> bool:
        """Evaluate a single condition definition against the agent's current state."""
        try:
            condition_query = """
            SELECT ?sensor_rdf ?operator_rdf ?value_rdf_node
            WHERE {
                ?condition_param lapras:hasSensor ?sensor_rdf .
                ?condition_param lapras:hasOperator ?operator_rdf .
                ?condition_param lapras:hasValue ?value_rdf_node .
            }"""
            
            query_results = list(self.rules_graph.query(
                condition_query, initBindings={'condition_param': condition_node}
            ))

            if not query_results:
                logger.warning(f"[{self.service_id}] No specific (sensor, operator, value) found for condition node {condition_node} in RDF graph.")
                return False
            
            sensor_rdf, operator_rdf, value_rdf_node = query_results[0]
            
            sensor_id_from_rule = str(sensor_rdf)
            operator_str = str(operator_rdf).split('/')[-1]
            
            value_from_agent_state = current_agent_state.get(sensor_id_from_rule)

            if value_from_agent_state is None:
                logger.info(f"[{self.service_id}] Sensor '{sensor_id_from_rule}' (for condition '{condition_node}') not found in agent state: {current_agent_state}")
                return False

            rule_threshold_value = None
            if isinstance(value_rdf_node, rdflib.Literal):
                rule_threshold_value = value_rdf_node.value
            else:
                logger.warning(f"[{self.service_id}] Rule value for sensor '{sensor_id_from_rule}' in condition '{condition_node}' is not an RDF Literal: {value_rdf_node}")
                return False
            
            logger.debug(f"[{self.service_id}]   Cond Check Details: Sensor='{sensor_id_from_rule}', Op='{operator_str}', AgentVal='{value_from_agent_state}' (type {type(value_from_agent_state).__name__}), RuleVal='{rule_threshold_value}' (type {type(rule_threshold_value).__name__})")
            
            result = False
            try:
                if operator_str in ["greaterThan", "lessThan", "greaterThanOrEqual", "lessThanOrEqual"]:
                    val_state_num = float(value_from_agent_state)
                    rule_val_num = float(rule_threshold_value)
                    if operator_str == "greaterThan": result = val_state_num > rule_val_num
                    elif operator_str == "lessThan": result = val_state_num < rule_val_num
                    elif operator_str == "greaterThanOrEqual": result = val_state_num >= rule_val_num
                    elif operator_str == "lessThanOrEqual": result = val_state_num <= rule_val_num
                
                elif operator_str == "equals":
                    try:
                        val_state_num = float(value_from_agent_state)
                        rule_val_num = float(rule_threshold_value)
                        result = (val_state_num == rule_val_num)
                    except (ValueError, TypeError):
                        result = str(value_from_agent_state) == str(rule_threshold_value)
                
                elif operator_str == "notEquals":
                    try:
                        val_state_num = float(value_from_agent_state)
                        rule_val_num = float(rule_threshold_value)
                        result = (val_state_num != rule_val_num)
                    except (ValueError, TypeError):
                        result = str(value_from_agent_state) != str(rule_threshold_value)
                else:
                    logger.warning(f"[{self.service_id}] Unsupported operator '{operator_str}' for comparison in condition '{condition_node}'.")
                    return False
            except (ValueError, TypeError) as e:
                logger.warning(f"[{self.service_id}] Type error during comparison for sensor '{sensor_id_from_rule}' in condition '{condition_node}': {e}. AgentVal='{value_from_agent_state}', RuleVal='{rule_threshold_value}'")
                return False
            
            logger.debug(f"[{self.service_id}]   Condition evaluation: ('{value_from_agent_state}' {operator_str} '{rule_threshold_value}') = {result}")
            return result 
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error evaluating condition node '{condition_node}': {e}", exc_info=True)
            return False

    def _parse_action(self, action_uri: rdflib.term.Node) -> Optional[Dict[str, Any]]:
        """Parse an action node to find a state_update JSON string."""
        try:
            action_query = """
            SELECT ?state_update_json_str
            WHERE {
                ?action_param lapras:hasStateUpdate ?state_update_json_str .
            }
            """
            query_results = list(self.rules_graph.query(
                action_query, initBindings={'action_param': action_uri}
            ))

            if not query_results:
                logger.debug(f"[{self.service_id}] No 'lapras:hasStateUpdate' found for action URI: {action_uri}")
                return None
            
            state_update_json_str_literal = query_results[0][0]
            if not isinstance(state_update_json_str_literal, rdflib.Literal):
                logger.error(f"[{self.service_id}] Expected RDF Literal for state_update, got {type(state_update_json_str_literal)} for action {action_uri}")
                return None

            state_update_json_str = str(state_update_json_str_literal.value)

            try:
                parsed_state_update = json.loads(state_update_json_str)
                if not isinstance(parsed_state_update, dict):
                    logger.error(f"[{self.service_id}] 'state_update' for action {action_uri} is not a JSON object (dict): {state_update_json_str}")
                    return None
                return {"state_update": parsed_state_update}
            except json.JSONDecodeError as je:
                logger.error(f"[{self.service_id}] Invalid JSON in state_update for action {action_uri}: '{state_update_json_str}'. Error: {je}")
                return None
        
        except Exception as e:
            logger.error(f"[{self.service_id}] Error parsing action {action_uri}: {e}", exc_info=True)
            return None

    def load_rules(self, rdf_file_path: str) -> None:
        """Load rules from an RDF file."""
        try:
            self.rules_graph.parse(rdf_file_path, format="turtle")
            logger.info(f"[{self.service_id}] Successfully loaded rules from {rdf_file_path}")
            
            # Log loaded rule details for verification
            rules_query = """
            SELECT ?rule_uri ?agent_literal (GROUP_CONCAT(?condition_uri; separator=", ") AS ?conditions) ?action_uri
            WHERE {
                ?rule_uri rdf:type lapras:Rule .
                ?rule_uri lapras:hasAgent ?agent_literal .
                OPTIONAL { ?rule_uri lapras:hasCondition ?condition_uri . }
                OPTIONAL { ?rule_uri lapras:hasAction ?action_uri . }
            }
            GROUP BY ?rule_uri ?agent_literal ?action_uri
            """
            logger.debug(f"[{self.service_id}] Verifying loaded rules:")
            for r_uri, ag_lit, conds_str, act_uri in self.rules_graph.query(rules_query):
                logger.debug(f"[{self.service_id}]   Rule: {r_uri}, Agent: {ag_lit}, Conditions: [{conds_str if conds_str else 'None'}], Action: {act_uri if act_uri else 'None'}")

        except Exception as e:
            logger.error(f"[{self.service_id}] Failed to load rules from {rdf_file_path}: {e}", exc_info=True)

    # Context management methods
    def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get the current state of an agent."""
        with self.context_lock:
            agent_data = self.context_map.get(agent_id)
            return agent_data["state"] if agent_data else None
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get the current states of all agents."""
        with self.context_lock:
            return {
                agent_id: data["state"]
                for agent_id, data in self.context_map.items()
            }
    
    def get_agent_last_update(self, agent_id: str) -> Optional[float]:
        """Get the last update time of an agent."""
        with self.context_lock:
            agent_data = self.context_map.get(agent_id)
            return agent_data["last_update"] if agent_data else None

    def stop(self) -> None:
        """Stop the context rule manager."""
        logger.info(f"[{self.service_id}] Stopping context rule manager...")
        if hasattr(self, 'mqtt_client') and self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info(f"[{self.service_id}] MQTT client disconnected.")
        logger.info(f"[{self.service_id}] Context rule manager stopped.") 
