import logging
import time
import json
import threading
from typing import Dict, Any, Optional, List
import uuid

import paho.mqtt.client as mqtt
import rdflib
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD

from .event import EventFactory, MQTTMessage, TopicManager, ContextPayload, ActionReportPayload, Event, EventMetadata, EntityInfo

logger = logging.getLogger(__name__)

class ContextRuleManager:
    """Combined context manager and rule executor that processes context states and applies rules."""

    def __init__(self, mqtt_broker: str = "143.248.57.73", mqtt_port: int = 1883, rule_files: Optional[List[str]] = None):
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
        
        # Track loaded rule files to avoid duplicates
        self.loaded_rule_files: set = set()
        
        # Track known virtual agents for dynamic topic subscription
        self.known_agents: set = set()
        
        # Track last action commands sent to prevent redundancy
        self.last_action_commands: Dict[str, Dict[str, Any]] = {}  # agent_id -> {action_name: params, timestamp: time}
        self.action_command_lock = threading.Lock()
        
        # Extended window logic for agents (15-second timing)
        self.extended_window_agents: Dict[str, Dict[str, Any]] = {}  # agent_id -> {start_time, duration, last_extend_time}
        self.extended_window_lock = threading.Lock()
        self.EXTENDED_WINDOW_DURATION = 15.0  # 15 seconds
        
        # Set up MQTT client with a unique client ID
        mqtt_client_id = f"{self.service_id}-{int(time.time()*1000)}"
        self.mqtt_client = mqtt.Client(client_id=mqtt_client_id)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        
        # Enable logging for MQTT client (for debugging)
        self.mqtt_client.enable_logger(logger)
        
        try:
            self.mqtt_client.connect(mqtt_broker, mqtt_port)
        except Exception as e:
            logger.error(f"[{self.service_id}] MQTT connection error: {e}", exc_info=True)
            raise

        # Start MQTT client loop
        self.mqtt_client.loop_start()
        logger.info(f"[{self.service_id}] Initialized with client ID: {mqtt_client_id} and connected to MQTT broker.")
        
        # Load initial rule files if provided
        if rule_files:
            for rule_file in rule_files:
                self.load_rules(rule_file)

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            logger.info(f"[{self.service_id}] Successfully connected to MQTT broker.")
            # Subscribe to updateContext events from all virtual agents using wildcard
            # Topic pattern: virtual/+/to/context/updateContext
            context_topic_pattern = "virtual/+/to/context/updateContext"
            result = self.mqtt_client.subscribe(context_topic_pattern, qos=1)  # Use QoS 1 for reliable delivery
            logger.info(f"[{self.service_id}] Subscribed to topic pattern: {context_topic_pattern} (result: {result})")
            
            # Subscribe to actionReport events from all virtual agents using wildcard
            # Topic pattern: virtual/+/to/context/actionReport
            report_topic_pattern = "virtual/+/to/context/actionReport"
            result2 = self.mqtt_client.subscribe(report_topic_pattern, qos=1)  # Use QoS 1 for reliable delivery
            logger.info(f"[{self.service_id}] Subscribed to topic pattern: {report_topic_pattern} (result: {result2})")
            
            # Subscribe to dashboard manual control commands
            # Topic: dashboard/control/command
            dashboard_control_topic = "dashboard/control/command"
            result3 = self.mqtt_client.subscribe(dashboard_control_topic, qos=1)
            logger.info(f"[{self.service_id}] Subscribed to dashboard control topic: {dashboard_control_topic} (result: {result3})")
            
            # Subscribe to rules management commands
            # Topic: context/rules/command
            rules_management_topic = "context/rules/command"
            result4 = self.mqtt_client.subscribe(rules_management_topic, qos=1)
            logger.info(f"[{self.service_id}] Subscribed to rules management topic: {rules_management_topic} (result: {result4})")
        else:
            logger.error(f"[{self.service_id}] Failed to connect to MQTT broker. Result code: {rc}")

    def _on_message(self, client, userdata, msg):
        """Callback when message is received from virtual agents or dashboard."""
        logger.info(f"[{self.service_id}] DEBUG: Message received on topic '{msg.topic}' with QoS {msg.qos}")
        logger.debug(f"[{self.service_id}] Message payload: {msg.payload.decode()[:200]}...")  # First 200 chars
        try:
            # Check if it's a dashboard control command
            if msg.topic == "dashboard/control/command":
                logger.info(f"[{self.service_id}] DEBUG: Processing dashboard control command")
                self._handle_dashboard_control_command(msg.payload.decode())
                return
            
            # Check if it's a rules management command
            if msg.topic == "context/rules/command":
                logger.info(f"[{self.service_id}] DEBUG: Processing rules management command")
                self._handle_rules_management_command(msg.payload.decode())
                return
            
            event = MQTTMessage.deserialize(msg.payload.decode())
            logger.info(f"[{self.service_id}] DEBUG: Event type: {event.event.type}, Source: {event.source.entityId}")
            
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

    def _handle_dashboard_control_command(self, message_payload: str):
        """Handle manual control command from dashboard via MQTT."""
        try:
            # Parse as Event structure instead of custom JSON
            event = MQTTMessage.deserialize(message_payload)
            
            if event.event.type != "dashboardCommand":
                logger.error(f"[{self.service_id}] Expected dashboardCommand event type, got: {event.event.type}")
                return
            
            logger.info(f"[{self.service_id}] Received dashboard control command: {event.event.id}")
            
            # Extract command details from payload
            agent_id = event.payload.get('agent_id')
            action_name = event.payload.get('action_name') 
            parameters = event.payload.get('parameters')
            priority = event.payload.get('priority', 'High')
            command_id = event.event.id
            
            if not agent_id or not action_name:
                logger.error(f"[{self.service_id}] Dashboard command missing required fields: {event.payload}")
                self._publish_dashboard_command_result(command_id, False, "Missing agent_id or action_name", agent_id)
                return
            
            # Check if agent exists
            if agent_id not in self.known_agents:
                logger.warning(f"[{self.service_id}] Dashboard command for unknown agent: {agent_id}")
                self._publish_dashboard_command_result(command_id, False, f"Agent {agent_id} not found", agent_id)
                return
            
            # Create and send action command
            action_event = EventFactory.create_action_event(
                virtual_agent_id=agent_id,
                action_name=action_name,
                parameters=parameters,
                priority=priority
            )
            
            # Send to virtual agent
            action_topic = TopicManager.context_to_virtual_action(agent_id)
            action_message = MQTTMessage.serialize(action_event)
            publish_result = self.mqtt_client.publish(action_topic, action_message, qos=1)
            
            # Log the dashboard command for audit trail
            logger.info(f"[{self.service_id}] DASHBOARD COMMAND sent to {agent_id}: {action_name}")
            if parameters:
                logger.info(f"[{self.service_id}] Command parameters: {parameters}")
            logger.info(f"[{self.service_id}] Command ID: {action_event.event.id}, Priority: {priority}")
            
            # Publish success result back to dashboard
            self._publish_dashboard_command_result(
                command_id, True, 
                f"Command '{action_name}' sent to {agent_id}", 
                agent_id, action_event.event.id
            )
            
        except json.JSONDecodeError:
            logger.error(f"[{self.service_id}] Invalid JSON in dashboard command: {message_payload}")
            self._publish_dashboard_command_result("unknown", False, "Invalid JSON format", None)
        except Exception as e:
            logger.error(f"[{self.service_id}] Error processing dashboard command: {e}", exc_info=True)
            self._publish_dashboard_command_result("unknown", False, f"Error: {str(e)}", None)

    def _publish_dashboard_command_result(self, command_id: str, success: bool, message: str, agent_id: Optional[str], action_event_id: Optional[str] = None):
        """Publish command result back to dashboard via MQTT using Event structure."""
        try:
            # Create Event structure for command result
            result_event = Event(
                event=EventMetadata(
                    id="",  # Auto-generated
                    timestamp="",  # Auto-generated  
                    type="dashboardCommandResult"
                ),
                source=EntityInfo(
                    entityType="contextManager",
                    entityId="CM-MainController"
                ),
                payload={
                    "command_id": command_id,
                    "success": success,
                    "message": message,
                    "agent_id": agent_id,
                    "action_event_id": action_event_id
                }
            )
            
            result_topic = "dashboard/control/result"
            result_message = MQTTMessage.serialize(result_event)
            self.mqtt_client.publish(result_topic, result_message, qos=1)
            
            logger.info(f"[{self.service_id}] Published dashboard command result: {command_id} - {success}")
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error publishing dashboard command result: {e}")

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
                logger.info(f"[{self.service_id}] Updated context for agent {agent_id}, context payload {context_payload.state}")
                logger.debug(f"[{self.service_id}] Current context map: {json.dumps(self.context_map, indent=2)}")
            
            # Track this agent for future action commands
            self.known_agents.add(agent_id)
            
            # Publish updated dashboard state
            self._publish_dashboard_state_update()
            
            # Immediately apply rules for this agent
            self._apply_rules_for_agent(agent_id, context_payload.state, event.event.timestamp)
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error handling context update: {e}", exc_info=True)

    def _publish_dashboard_state_update(self):
        """Publish current system state to dashboard via MQTT using Event structure."""
        try:
            with self.context_lock:
                # Create Event structure for dashboard state
                dashboard_state_event = Event(
                    event=EventMetadata(
                        id="",  # Auto-generated
                        timestamp="",  # Auto-generated
                        type="dashboardStateUpdate"
                    ),
                    source=EntityInfo(
                        entityType="contextManager",
                        entityId="CM-MainController"
                    ),
                    payload={
                        "agents": {},
                        "summary": {
                            "total_agents": len(self.context_map),
                            "known_agents": list(self.known_agents),
                            "last_update": time.time()
                        }
                    }
                )
                
                # Add agent states to payload
                for agent_id, agent_data in self.context_map.items():
                    dashboard_state_event.payload["agents"][agent_id] = {
                        "state": agent_data["state"],
                        "agent_type": agent_data["agent_type"], 
                        "sensors": agent_data["sensors"],
                        "timestamp": agent_data["timestamp"],
                        "last_update": agent_data["last_update"],
                        "is_responsive": (time.time() - agent_data["last_update"]) < 300  # 5 minute timeout
                    }
            
            # Publish using Event structure
            dashboard_topic = "dashboard/context/state"
            dashboard_message = MQTTMessage.serialize(dashboard_state_event)
            self.mqtt_client.publish(dashboard_topic, dashboard_message, qos=1)
            
            logger.debug(f"[{self.service_id}] Published dashboard state update with {len(dashboard_state_event.payload['agents'])} agents")
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error publishing dashboard state: {e}", exc_info=True)

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
        """Apply rules for a specific agent with 15-second extended window logic."""
        try:
            logger.debug(f"[{self.service_id}] Processing rules for agent '{agent_id}' (state updated)")
            logger.debug(f"[{self.service_id}] Current state for '{agent_id}': {json.dumps(current_state, indent=2)}")
            
            # Evaluate rules to get the raw decision
            raw_rule_decision = self.evaluate_rules(agent_id, current_state)
            
            if raw_rule_decision is None:
                logger.debug(f"[{self.service_id}] No rules triggered for agent '{agent_id}'")
                return
            
            # Extract power decision from rules
            raw_power_decision = raw_rule_decision.get("power")
            current_power_state = current_state.get("power", "off")
            
            logger.info(f"[{self.service_id}] Raw rule decision for '{agent_id}': power={raw_power_decision}")
            
            # Apply extended window logic
            final_decision = self._apply_extended_window_logic(agent_id, current_power_state, raw_power_decision)
            
            if final_decision != current_power_state:
                logger.info(f"[{self.service_id}] Final decision for '{agent_id}': {current_power_state} → {final_decision}")
                
                # Send action command based on final decision
                if final_decision == "on":
                    self._send_action_command(agent_id, "turn_on")
                elif final_decision == "off":
                    self._send_action_command(agent_id, "turn_off")
            else:
                logger.debug(f"[{self.service_id}] No state change needed for agent '{agent_id}' (already {current_power_state})")
                
        except Exception as e:
            logger.error(f"[{self.service_id}] Error applying rules for agent '{agent_id}': {e}", exc_info=True)

    def _apply_extended_window_logic(self, agent_id: str, current_power: str, raw_rule_decision: str) -> str:
        """
        Apply 15-second extended window logic to rule decisions.
        
        Logic:
        - OFF → ON: Start 15s window, return "on"
        - During 15s window:
          - Rule says "on": Extend window by 15s, return "on" 
          - Rule says "off": Continue countdown, return "on"
        - After 15s expires: Allow "off", return "off"
        """
        current_time = time.time()
        
        with self.extended_window_lock:
            window_info = self.extended_window_agents.get(agent_id)
            
            # Case 1: OFF → ON (start new window)
            if current_power == "off" and raw_rule_decision == "on":
                self.extended_window_agents[agent_id] = {
                    "start_time": current_time,
                    "duration": self.EXTENDED_WINDOW_DURATION,
                    "last_extend_time": current_time
                }
                logger.info(f"[{self.service_id}] Started 15s extended window for '{agent_id}'")
                return "on"
            
            # Case 2: No active window, follow raw decision
            if not window_info:
                return raw_rule_decision
            
            # Case 3: Active window - check if expired
            window_start = window_info["start_time"]
            last_extend = window_info["last_extend_time"]
            time_since_last_extend = current_time - last_extend
            
            # Window expired?
            if time_since_last_extend >= self.EXTENDED_WINDOW_DURATION:
                # Window expired - remove it and allow raw decision
                del self.extended_window_agents[agent_id]
                logger.info(f"[{self.service_id}] Extended window expired for '{agent_id}' - allowing raw decision: {raw_rule_decision}")
                return raw_rule_decision
            
            # Case 4: Active window, rule says "on" - extend window
            if raw_rule_decision == "on":
                self.extended_window_agents[agent_id]["last_extend_time"] = current_time
                remaining_time = self.EXTENDED_WINDOW_DURATION - time_since_last_extend
                logger.info(f"[{self.service_id}] Extended window for '{agent_id}' (was {remaining_time:.1f}s remaining, now reset to 15s)")
                return "on"
            
            # Case 5: Active window, rule says "off" - continue countdown, stay on
            else:
                remaining_time = self.EXTENDED_WINDOW_DURATION - time_since_last_extend
                logger.info(f"[{self.service_id}] Rule says 'off' for '{agent_id}', but in extended window ({remaining_time:.1f}s remaining) - staying on")
                return "on"

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

    def _is_action_redundant(self, agent_id: str, action_name: str, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """Check if this action command is redundant (same as the last one sent)."""
        with self.action_command_lock:
            if agent_id not in self.last_action_commands:
                return False  # No previous command, so not redundant
            
            last_command = self.last_action_commands[agent_id]
            
            # Check if it's the same action with the same parameters
            if (last_command.get("action_name") == action_name and 
                last_command.get("parameters") == parameters):
                
                # Also check if it was sent recently (within last 5 seconds)
                # This prevents sending the same command due to rapid sensor updates
                time_since_last = time.time() - last_command.get("timestamp", 0)
                if time_since_last < 5.0:  # 5 second cooldown
                    return True  # Redundant
            
            return False  # Not redundant
    
    def _record_action_command(self, agent_id: str, action_name: str, parameters: Optional[Dict[str, Any]] = None):
        """Record that we sent this action command to prevent future redundancy."""
        with self.action_command_lock:
            self.last_action_commands[agent_id] = {
                "action_name": action_name,
                "parameters": parameters,
                "timestamp": time.time()
            }

    def _send_action_command(self, agent_id: str, action_name: str, parameters: Optional[Dict[str, Any]] = None):
        """Send an action command to a VirtualAgent (SYNCHRONOUS - Request)."""
        try:
            # Check if this action command is redundant
            if self._is_action_redundant(agent_id, action_name, parameters):
                logger.info(f"[{self.service_id}] Skipping redundant action command '{action_name}' to agent '{agent_id}'")
                return
            
            # Create applyAction event
            action_event = EventFactory.create_action_event(
                virtual_agent_id=agent_id,
                action_name=action_name,
                parameters=parameters
            )
            
            # Publish to the agent's action topic
            action_topic = TopicManager.context_to_virtual_action(agent_id)
            action_message = MQTTMessage.serialize(action_event)
            self.mqtt_client.publish(action_topic, action_message, qos=1)  # Use QoS 1 for reliable delivery
            
            # Record this command to prevent future redundancy
            self._record_action_command(agent_id, action_name, parameters)
            
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
            logger.info(f"[{self.service_id}] Evaluating rules for agent '{agent_id}'")

            for rule_uri, action_uri in self.rules_graph.query(
                agent_specific_rules_query,
                initBindings={'agent_id_param': agent_id_rdf_literal}
            ):
                rule_name_short = str(rule_uri).split('/')[-1] or str(rule_uri)
                logger.debug(f"[{self.service_id}] Checking rule '{rule_name_short}' for agent '{agent_id}'")

                rule_conditions_query = """
                SELECT ?condition_node
                WHERE { ?current_rule_param lapras:hasCondition ?condition_node . }
                """
                conditions_for_this_rule = list(self.rules_graph.query(
                    rule_conditions_query, initBindings={'current_rule_param': rule_uri}
                ))

                if not conditions_for_this_rule:
                    logger.debug(f"[{self.service_id}] Rule '{rule_name_short}' has no conditions - skipping")
                    continue

                all_conditions_met_for_this_rule = True
                for i, condition_row in enumerate(conditions_for_this_rule):
                    condition_node = condition_row[0]
                    if not self._evaluate_condition(condition_node, current_state):
                        all_conditions_met_for_this_rule = False
                        logger.debug(f"[{self.service_id}] Rule '{rule_name_short}' condition #{i+1} failed")
                        break

                if all_conditions_met_for_this_rule:
                    action_data = self._parse_action(action_uri)
                    logger.info(f"[{self.service_id}] Rule '{rule_name_short}' Action '{action_data}' ALL conditions met - applying action")

                    if action_data and "state_update" in action_data:
                        state_update_payload = action_data["state_update"]
                        if isinstance(state_update_payload, dict):
                            # Check if the state update actually changes anything
                            changed_by_this_action = False
                            for key, value in state_update_payload.items():
                                logger.info(f"[{self.service_id}] Rule '{rule_name_short}' state update changes {key} from {new_state_after_all_rules.get(key)} to {value}")
                                if new_state_after_all_rules.get(key) != value:
                                    changed_by_this_action = True
                                    break
                            
                            if changed_by_this_action:
                                logger.info(f"[{self.service_id}] Applying state update for rule '{rule_name_short}': {json.dumps(state_update_payload)}")
                                new_state_after_all_rules.update(state_update_payload)
                                any_rule_led_to_actionable_change = True
                            else:
                                logger.debug(f"[{self.service_id}] Rule '{rule_name_short}' state update doesn't change current state")
                        else:
                            logger.warning(f"[{self.service_id}] Rule '{rule_name_short}' state_update is not a dictionary")
                    else:
                        logger.warning(f"[{self.service_id}] Rule '{rule_name_short}' missing state_update data")

            if any_rule_led_to_actionable_change:
                logger.info(f"[{self.service_id}] Final state for agent '{agent_id}' after rules: {json.dumps(new_state_after_all_rules)}")
                return new_state_after_all_rules
            else:
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
                logger.debug(f"[{self.service_id}] No sensor/operator/value found for condition {condition_node}")
                return False
            
            sensor_rdf, operator_rdf, value_rdf_node = query_results[0]
            
            sensor_id_from_rule = str(sensor_rdf)
            operator_str = str(operator_rdf).split('/')[-1]
            
            value_from_agent_state = current_agent_state.get(sensor_id_from_rule)

            if value_from_agent_state is None:
                logger.debug(f"[{self.service_id}] Sensor '{sensor_id_from_rule}' not found in agent state")
                return False

            rule_threshold_value = None
            if isinstance(value_rdf_node, rdflib.Literal):
                rule_threshold_value = value_rdf_node.value
            else:
                logger.debug(f"[{self.service_id}] Rule value for '{sensor_id_from_rule}' is not a literal")
                return False
            
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
                    logger.debug(f"[{self.service_id}] Unsupported operator '{operator_str}'")
                    return False
            except (ValueError, TypeError) as e:
                logger.debug(f"[{self.service_id}] Type error in condition evaluation: {e}")
                return False
            
            # Only log condition details when they're true (to reduce log spam)
            if result:
                logger.debug(f"[{self.service_id}] Condition TRUE: '{value_from_agent_state}' {operator_str} '{rule_threshold_value}'")
            
            return result 
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error evaluating condition: {e}", exc_info=True)
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
            # Check if file already loaded to avoid duplicates
            if rdf_file_path in self.loaded_rule_files:
                logger.info(f"[{self.service_id}] Rules file {rdf_file_path} already loaded, skipping")
                return
            
            self.rules_graph.parse(rdf_file_path, format="turtle")
            self.loaded_rule_files.add(rdf_file_path)
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
            logger.debug(f"[{self.service_id}] Verifying loaded rules from {rdf_file_path}:")
            for r_uri, ag_lit, conds_str, act_uri in self.rules_graph.query(rules_query):
                logger.debug(f"[{self.service_id}]   Rule: {r_uri}, Agent: {ag_lit}, Conditions: [{conds_str if conds_str else 'None'}], Action: {act_uri if act_uri else 'None'}")

        except Exception as e:
            logger.error(f"[{self.service_id}] Failed to load rules from {rdf_file_path}: {e}", exc_info=True)

    def load_rules_from_list(self, rule_file_paths: List[str]) -> Dict[str, bool]:
        """Load multiple rule files and return success status for each."""
        results = {}
        for rule_file in rule_file_paths:
            try:
                self.load_rules(rule_file)
                results[rule_file] = True
            except Exception as e:
                logger.error(f"[{self.service_id}] Failed to load rule file {rule_file}: {e}")
                results[rule_file] = False
        return results

    def get_loaded_rule_files(self) -> List[str]:
        """Get list of currently loaded rule files."""
        return list(self.loaded_rule_files)

    def clear_rules(self) -> None:
        """Clear all loaded rules."""
        self.rules_graph = Graph()
        self.rules_graph.bind("lapras", self.lapras)
        self.loaded_rule_files.clear()
        logger.info(f"[{self.service_id}] All rules cleared")

    def _handle_rules_management_command(self, message_payload: str):
        """Handle rules management commands via MQTT."""
        try:
            event = MQTTMessage.deserialize(message_payload)
            
            if event.event.type != "rulesCommand":
                logger.error(f"[{self.service_id}] Expected rulesCommand event type, got: {event.event.type}")
                return
            
            logger.info(f"[{self.service_id}] Received rules management command: {event.event.id}")
            
            # Extract command details from payload
            command_action = event.payload.get('action')  # "load", "unload", "reload", "list"
            rule_files = event.payload.get('rule_files', [])  # list of rule file paths
            command_id = event.event.id
            
            success = False
            message = ""
            
            if command_action == "load":
                try:
                    loaded_files = []
                    for rule_file in rule_files:
                        self.load_rules(rule_file)
                        loaded_files.append(rule_file)
                    success = True
                    message = f"Successfully loaded {len(loaded_files)} rule files: {loaded_files}"
                except Exception as e:
                    message = f"Error loading rules: {str(e)}"
                    
            elif command_action == "reload":
                try:
                    # Clear existing rules
                    self.rules_graph = Graph()
                    self.rules_graph.bind("lapras", self.lapras)
                    self.loaded_rule_files.clear()
                    
                    # Reload specified files
                    loaded_files = []
                    for rule_file in rule_files:
                        self.load_rules(rule_file)
                        loaded_files.append(rule_file)
                    success = True
                    message = f"Successfully reloaded {len(loaded_files)} rule files: {loaded_files}"
                except Exception as e:
                    message = f"Error reloading rules: {str(e)}"
                    
            elif command_action == "list":
                success = True
                message = f"Currently loaded rule files: {list(self.loaded_rule_files)}"
                
            else:
                message = f"Unknown rules command action: {command_action}"
            
            # Publish result back
            self._publish_rules_command_result(command_id, success, message, command_action)
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error processing rules management command: {e}", exc_info=True)
            self._publish_rules_command_result("unknown", False, f"Error: {str(e)}", "unknown")

    def _publish_rules_command_result(self, command_id: str, success: bool, message: str, action: str):
        """Publish rules command result back via MQTT using Event structure."""
        try:
            result_event = Event(
                event=EventMetadata(
                    id="",  # Auto-generated
                    timestamp="",  # Auto-generated  
                    type="rulesCommandResult"
                ),
                source=EntityInfo(
                    entityType="contextManager",
                    entityId="CM-MainController"
                ),
                payload={
                    "command_id": command_id,
                    "success": success,
                    "message": message,
                    "action": action,
                    "loaded_files": list(self.loaded_rule_files)
                }
            )
            
            result_topic = "context/rules/result"
            result_message = MQTTMessage.serialize(result_event)
            self.mqtt_client.publish(result_topic, result_message, qos=1)
            
            logger.info(f"[{self.service_id}] Published rules command result: {command_id} - {success}")
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error publishing rules command result: {e}")

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

    def send_manual_command(self, agent_id: str, action_name: str, 
                           parameters: Optional[Dict[str, Any]] = None,
                           priority: str = "High") -> Dict[str, Any]:
        """
        Send a manual control command from dashboard/API to a virtual agent.
        
        Args:
            agent_id: Target virtual agent ID
            action_name: Action to perform (e.g., "turn_on", "set_temperature")
            parameters: Optional action parameters
            priority: Command priority (Low|Normal|High|Critical)
            
        Returns:
            Dict with command_id, success status, and message
        """
        try:
            # Check if agent exists in our known agents
            if agent_id not in self.known_agents:
                logger.warning(f"[{self.service_id}] Manual command attempted for unknown agent: {agent_id}")
                return {
                    "success": False,
                    "command_id": None,
                    "message": f"Agent {agent_id} not found or not connected",
                    "agent_id": agent_id
                }
            
            # Create and send action command with specified priority
            action_event = EventFactory.create_action_event(
                virtual_agent_id=agent_id,
                action_name=action_name,
                parameters=parameters,
                priority=priority  # Manual commands typically get higher priority
            )
            
            # Send via MQTT to the specific agent
            action_topic = TopicManager.context_to_virtual_action(agent_id)
            action_message = MQTTMessage.serialize(action_event)
            publish_result = self.mqtt_client.publish(action_topic, action_message, qos=1)
            
            # Log the manual command for audit trail
            logger.info(f"[{self.service_id}] MANUAL COMMAND sent to {agent_id}: {action_name}")
            if parameters:
                logger.info(f"[{self.service_id}] Command parameters: {parameters}")
            logger.info(f"[{self.service_id}] Command ID: {action_event.event.id}, Priority: {priority}")
            
            return {
                "success": True,
                "command_id": action_event.event.id,
                "message": f"Manual command '{action_name}' sent to {agent_id}",
                "action_name": action_name,
                "agent_id": agent_id,
                "priority": priority,
                "publish_result": str(publish_result)
            }
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error sending manual command to {agent_id}: {e}", exc_info=True)
            return {
                "success": False,
                "command_id": None,
                "message": f"Error sending command: {str(e)}",
                "agent_id": agent_id
            }

    def get_known_agents(self) -> list:
        """
        Get list of known/connected agents for dashboard display.
        
        Returns:
            List of agent IDs that have sent context updates
        """
        return list(self.known_agents)

    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete information about a specific agent including metadata.
        
        Args:
            agent_id: The agent ID to get information for
            
        Returns:
            Dict with agent state, type, sensors, timestamps, etc.
            None if agent not found
        """
        with self.context_lock:
            agent_data = self.context_map.get(agent_id)
            if agent_data:
                return {
                    "agent_id": agent_id,
                    "state": agent_data["state"],
                    "agent_type": agent_data["agent_type"],
                    "sensors": agent_data["sensors"],
                    "timestamp": agent_data["timestamp"],
                    "last_update": agent_data["last_update"],
                    "is_responsive": (time.time() - agent_data["last_update"]) < 300  # 5 minute timeout
                }
            return None 