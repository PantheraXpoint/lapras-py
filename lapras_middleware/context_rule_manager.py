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
        
        # Define rule presets for easy switching
        self.rule_presets = {
            "hue_motion_only": ["lapras_middleware/rules/hue_motion.ttl"],
            "hue_activity_only": ["lapras_middleware/rules/hue_activity.ttl"],
            "hue_ir_only": ["lapras_middleware/rules/hue_ir.ttl"],
            "hue_ir_motion": ["lapras_middleware/rules/hue_ir_motion.ttl"],
            "hue_activity_motion": ["lapras_middleware/rules/hue_activity_motion.ttl"],
            "hue_ir_activity": ["lapras_middleware/rules/hue_ir_activity.ttl"],
            "hue_all_sensors": ["lapras_middleware/rules/hue_ir_activity_motion.ttl"],
            "aircon_motion_only": ["lapras_middleware/rules/aircon_motion.ttl"],
            "aircon_activity_only": ["lapras_middleware/rules/aircon_activity.ttl"],
            "aircon_ir_only": ["lapras_middleware/rules/aircon_ir.ttl"],
            "aircon_all_sensors": ["lapras_middleware/rules/aircon_ir_acitivity_motion.ttl"],
            "both_devices_motion": [
                "lapras_middleware/rules/hue_motion.ttl",
                "lapras_middleware/rules/aircon_motion.ttl"
            ],
            "both_devices_all": [
                "lapras_middleware/rules/hue_ir_activity_motion.ttl",
                "lapras_middleware/rules/aircon_ir_acitivity_motion.ttl"
            ]
        }
        
        # Track known virtual agents for dynamic topic subscription
        self.known_agents: set = set()
        
        # Track last action commands sent to prevent redundancy
        self.last_action_commands: Dict[str, Dict[str, Any]] = {}  # agent_id -> {action_name: params, timestamp: time}
        self.action_command_lock = threading.Lock()
        
        # Extended window logic for agents - configurable timing
        self.extended_window_agents: Dict[str, Dict[str, Any]] = {}  # agent_id -> {start_time, duration, last_extend_time}
        self.extended_window_lock = threading.Lock()
        # Fast state change: 15.0 for quick OFF response | Stable state: 60.0 for longer device ON time
        self.EXTENDED_WINDOW_DURATION = 60.0  # 60 seconds (change to 15.0 for fast OFF response)
        
        # Manual override tracking - REQUIREMENT: 120 to maintain manual state
        self.manual_override_agents: Dict[str, float] = {}  # agent_id -> override_expiry_time
        self.manual_override_lock = threading.Lock()
        self.MANUAL_OVERRIDE_DURATION = 120.0  # 120 seconds override after manual command
        
        # Set up MQTT client with a unique client ID and clean session
        mqtt_client_id = f"{self.service_id}-{int(time.time()*1000)}-{uuid.uuid4().hex[:8]}"
        self.mqtt_client = mqtt.Client(client_id=mqtt_client_id, clean_session=True)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_subscribe = self._on_subscribe
        self.mqtt_client.on_disconnect = self._on_disconnect
        
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
            dashboard_control_topic = TopicManager.dashboard_control_command()
            result3 = self.mqtt_client.subscribe(dashboard_control_topic, qos=1)
            logger.info(f"[{self.service_id}] Subscribed to dashboard control topic: {dashboard_control_topic} (result: {result3})")
            
            # Subscribe to rules management commands
            rules_management_topic = TopicManager.rules_management_command()
            result4 = self.mqtt_client.subscribe(rules_management_topic, qos=1)
            logger.info(f"[{self.service_id}] Subscribed to rules management topic: {rules_management_topic} (result: {result4})")
            
            # Subscribe to dashboard sensor configuration commands
            # Topic: dashboard/sensor/config/command
            sensor_config_topic = TopicManager.dashboard_sensor_config_command()
            result5 = self.mqtt_client.subscribe(sensor_config_topic, qos=1)
            logger.info(f"[{self.service_id}] Subscribed to sensor config topic: {sensor_config_topic} (result: {result5})")
            
            # Subscribe to threshold configuration commands from dashboard
            # Topic: dashboard/threshold/command
            threshold_config_topic = TopicManager.dashboard_threshold_command()
            result6 = self.mqtt_client.subscribe(threshold_config_topic, qos=1)
            logger.info(f"[{self.service_id}] Subscribed to threshold config topic: {threshold_config_topic} (result: {result6})")
            
            # Subscribe to sensor configuration results from virtual agents
            # Topic pattern: agent/+/sensorConfig/result
            sensor_config_result_pattern = "agent/+/sensorConfig/result"
            result7 = self.mqtt_client.subscribe(sensor_config_result_pattern, qos=1)
            logger.info(f"[{self.service_id}] Subscribed to sensor config result pattern: {sensor_config_result_pattern} (result: {result7})")
            
            # Subscribe to threshold configuration results from virtual agents
            # Topic pattern: agent/+/thresholdConfig/result
            threshold_config_result_pattern = "agent/+/thresholdConfig/result"
            result8 = self.mqtt_client.subscribe(threshold_config_result_pattern, qos=1)
            logger.info(f"[{self.service_id}] Subscribed to threshold config result pattern: {threshold_config_result_pattern} (result: {result8})")
        else:
            logger.error(f"[{self.service_id}] Failed to connect to MQTT broker. Result code: {rc}")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback when subscription is confirmed."""
        logger.info(f"[{self.service_id}] Subscription confirmed for message ID {mid} with QoS {granted_qos}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        if rc != 0:
            logger.warning(f"[{self.service_id}] Unexpected MQTT disconnection. Result code: {rc}")
        else:
            logger.info(f"[{self.service_id}] MQTT client disconnected normally")

    def _on_message(self, client, userdata, msg):
        """Callback when message is received from virtual agents or dashboard."""
        logger.info(f"[{self.service_id}] DEBUG: Message received on topic '{msg.topic}' with QoS {msg.qos}")
        logger.debug(f"[{self.service_id}] Message payload: {msg.payload.decode()[:200]}...")  # First 200 chars
        
        try:
            # Check if it's a dashboard control command
            if msg.topic == TopicManager.dashboard_control_command():
                logger.info(f"[{self.service_id}] DEBUG: Processing dashboard control command")
                self._handle_dashboard_control_command(msg.payload.decode())
                return
            
            # Check if it's a rules management command
            if msg.topic == TopicManager.rules_management_command():
                logger.info(f"[{self.service_id}] DEBUG: Processing rules management command")
                logger.debug(f"[{self.service_id}] Full rules command payload: {msg.payload.decode()}")
                try:
                    self._handle_rules_management_command(msg.payload.decode())
                    logger.info(f"[{self.service_id}] DEBUG: Rules management command processed successfully")
                except Exception as rules_error:
                    logger.error(f"[{self.service_id}] ERROR in rules management command: {rules_error}", exc_info=True)
                return
            
            # Check if it's a dashboard sensor configuration command
            if msg.topic == TopicManager.dashboard_sensor_config_command():
                logger.info(f"[{self.service_id}] DEBUG: Processing sensor configuration command")
                try:
                    self._handle_sensor_config_command(msg.payload.decode())
                    logger.info(f"[{self.service_id}] DEBUG: Sensor configuration command processed successfully")
                except Exception as sensor_error:
                    logger.error(f"[{self.service_id}] ERROR in sensor configuration command: {sensor_error}", exc_info=True)
                return
            
            # Check if it's a dashboard threshold configuration command
            if msg.topic == TopicManager.dashboard_threshold_command():
                logger.info(f"[{self.service_id}] DEBUG: Processing threshold configuration command")
                try:
                    self._handle_threshold_config_command(msg.payload.decode())
                    logger.info(f"[{self.service_id}] DEBUG: Threshold configuration command processed successfully")
                except Exception as threshold_error:
                    logger.error(f"[{self.service_id}] ERROR in threshold configuration command: {threshold_error}", exc_info=True)
                return
            
            # Check if it's a sensor configuration result from virtual agent
            if msg.topic.startswith("agent/") and msg.topic.endswith("/sensorConfig/result"):
                logger.info(f"[{self.service_id}] DEBUG: Processing sensor configuration result")
                try:
                    self._handle_sensor_config_result(msg.payload.decode())
                    logger.info(f"[{self.service_id}] DEBUG: Sensor configuration result processed successfully")
                except Exception as result_error:
                    logger.error(f"[{self.service_id}] ERROR in sensor configuration result: {result_error}", exc_info=True)
                return
            
            # Check if it's a threshold configuration result from virtual agent
            if msg.topic.startswith("agent/") and msg.topic.endswith("/thresholdConfig/result"):
                logger.info(f"[{self.service_id}] DEBUG: Processing threshold configuration result")
                try:
                    self._handle_threshold_config_result(msg.payload.decode())
                    logger.info(f"[{self.service_id}] DEBUG: Threshold configuration result processed successfully")
                except Exception as result_error:
                    logger.error(f"[{self.service_id}] ERROR in threshold configuration result: {result_error}", exc_info=True)
                return
            
            # For other message types, try to deserialize as Event
            logger.debug(f"[{self.service_id}] Attempting to deserialize message as Event structure")
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
                
        except json.JSONDecodeError as json_error:
            logger.error(f"[{self.service_id}] Message payload on topic '{msg.topic}' was not valid JSON: {msg.payload.decode(errors='ignore')}")
            logger.error(f"[{self.service_id}] JSON decode error: {json_error}")
        except Exception as e:
            logger.error(f"[{self.service_id}] Error processing message on topic '{msg.topic}': {e}", exc_info=True)
            logger.error(f"[{self.service_id}] Message payload that caused error: {msg.payload.decode(errors='ignore')}")

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
                parameters={**parameters, "skip_verification": True} if parameters else {"skip_verification": True},
                priority=priority
            )

            # Record manual override - NEW
            with self.manual_override_lock:
                self.manual_override_agents[agent_id] = time.time() + self.MANUAL_OVERRIDE_DURATION
            
            # Send to virtual agent using direct MQTT publish for manual commands (bypass redundancy check)
            action_topic = TopicManager.context_to_virtual_action(agent_id)
            action_message = MQTTMessage.serialize(action_event)
            publish_result = self.mqtt_client.publish(action_topic, action_message, qos=1)
            
            # Check if publish was successful
            if publish_result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"[{self.service_id}] Failed to publish action command to {agent_id}. Return code: {publish_result.rc}")
                self._publish_dashboard_command_result(command_id, False, f"Failed to send command to {agent_id}", agent_id)
                return
            
            
            # Log the dashboard command for audit trail
            logger.info(f"[{self.service_id}] DASHBOARD COMMAND sent to {agent_id}: {action_name}")
            logger.info(f"[{self.service_id}] Action topic: {action_topic}")
            logger.info(f"[{self.service_id}] Action event ID: {action_event.event.id}")
            logger.info(f"[{self.service_id}] Manual override active for {self.MANUAL_OVERRIDE_DURATION}s")
            if parameters:
                logger.info(f"[{self.service_id}] Command parameters: {parameters}")
            logger.info(f"[{self.service_id}] Command ID: {action_event.event.id}, Priority: {priority}")
            
            # Publish success result back to dashboard
            self._publish_dashboard_command_result(
                command_id, True, 
                f"Command '{action_name}' sent to {agent_id} on topic {action_topic}", 
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
            result_event = EventFactory.create_dashboard_command_result_event(
                command_id=command_id,
                success=success,
                message=message,
                agent_id=agent_id,
                action_event_id=action_event_id
            )
            
            result_topic = TopicManager.dashboard_control_result()
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
            
            logger.info(f"[{self.service_id}] 📨 CONTEXT UPDATE received from '{agent_id}'")
            
            # Check manual override status - NEW
            manual_override_active = False
            with self.manual_override_lock:
                override_expiry = self.manual_override_agents.get(agent_id)
                if override_expiry and time.time() < override_expiry:
                    manual_override_active = True
                    remaining_time = override_expiry - time.time()
                    logger.info(f"[{self.service_id}] ⚠️  CONTEXT UPDATE: Manual override active for '{agent_id}' ({remaining_time:.1f}s remaining)")
                elif override_expiry and time.time() >= override_expiry:
                    # Override expired, remove it
                    del self.manual_override_agents[agent_id]
                    logger.info(f"[{self.service_id}] Manual override expired for '{agent_id}' - automatic rules now resume")
            
            # Update context map
            with self.context_lock:
                new_state = context_payload.state.copy()
                
                # During manual override, allow all state changes to come through
                # This ensures manual commands are properly reflected in the system state
                if manual_override_active:
                    logger.info(f"[{self.service_id}] 📨 CONTEXT UPDATE: Manual override active for '{agent_id}' - accepting state update as-is: {new_state.get('power', 'unknown')}")
                else:
                    logger.info(f"[{self.service_id}] 📨 CONTEXT UPDATE: No manual override for '{agent_id}' - normal state update: {new_state.get('power', 'unknown')}")
                
                self.context_map[agent_id] = {
                    "state": new_state,
                    "agent_type": context_payload.agent_type,
                    "sensors": context_payload.sensors,
                    "timestamp": event.event.timestamp,
                    "last_update": time.time()
                }
                logger.info(f"[{self.service_id}] 📨 CONTEXT UPDATE: Updated context for agent {agent_id}, context payload {new_state}")
                logger.debug(f"[{self.service_id}] Current context map: {json.dumps(self.context_map, indent=2)}")
            
            # Track this agent for future action commands
            self.known_agents.add(agent_id)
            
            # Publish updated dashboard state
            self._publish_dashboard_state_update()
            
            # Immediately apply rules for this agent (will be skipped during override)
            logger.info(f"[{self.service_id}] 📨 CONTEXT UPDATE: About to apply rules for '{agent_id}' - manual override: {manual_override_active}")
            self._apply_rules_for_agent(agent_id, new_state, event.event.timestamp)
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error handling context update: {e}", exc_info=True)

    def _publish_dashboard_state_update(self):
        """Publish current system state to dashboard via MQTT using Event structure."""
        try:
            with self.context_lock:
                # Prepare agents data
                agents_data = {}
                for agent_id, agent_data in self.context_map.items():
                    agents_data[agent_id] = {
                        "state": agent_data["state"],
                        "agent_type": agent_data["agent_type"], 
                        "sensors": agent_data["sensors"],
                        "timestamp": agent_data["timestamp"],
                        "last_update": agent_data["last_update"],
                        "is_responsive": (time.time() - agent_data["last_update"]) < 300  # 5 minute timeout
                    }
                
                # Prepare summary data
                summary_data = {
                    "total_agents": len(self.context_map),
                    "known_agents": list(self.known_agents),
                    "last_update": time.time()
                }
                
                # Create Event structure for dashboard state
                dashboard_state_event = EventFactory.create_dashboard_state_update_event(
                    agents=agents_data,
                    summary=summary_data
                )
            
            # Publish using Event structure
            dashboard_topic = TopicManager.dashboard_context_state()
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
        """Apply rules for a specific agent with manual override check."""
        try:
            # Check if manual override is active (but don't block rule evaluation)
            manual_override_active = False
            remaining_time = 0
            with self.manual_override_lock:
                override_expiry = self.manual_override_agents.get(agent_id)
                if override_expiry and time.time() < override_expiry:
                    manual_override_active = True
                    remaining_time = override_expiry - time.time()
                    logger.info(f"[{self.service_id}] ⚠️  MANUAL OVERRIDE ACTIVE for '{agent_id}' ({remaining_time:.1f}s remaining) - rules will be evaluated but OFF commands blocked")
                elif override_expiry and time.time() >= override_expiry:
                    # Override expired, remove it
                    del self.manual_override_agents[agent_id]
                    logger.info(f"[{self.service_id}] Manual override expired for '{agent_id}' - automatic rules now resume")
            
            logger.info(f"[{self.service_id}] 🔍 DEBUG: Processing rules for agent '{agent_id}' (state updated)")
            logger.info(f"[{self.service_id}] 🔍 DEBUG: Current state for '{agent_id}': {json.dumps(current_state, indent=2)}")
            logger.info(f"[{self.service_id}] 🔍 DEBUG: Manual override active: {manual_override_active} ({remaining_time:.1f}s remaining)")
            
            # Evaluate rules to get the raw decision
            raw_rule_decision = self.evaluate_rules(agent_id, current_state)
            
            if raw_rule_decision is None:
                logger.debug(f"[{self.service_id}] No rules triggered for agent '{agent_id}'")
                return
            
            # Extract power decision from rules
            raw_power_decision = raw_rule_decision.get("power")
            current_power_state = current_state.get("power", "off")
            
            logger.info(f"[{self.service_id}] 🔍 DEBUG: Raw rule decision for '{agent_id}': power={raw_power_decision}")
            logger.info(f"[{self.service_id}] 🔍 DEBUG: Current power state for '{agent_id}': {current_power_state}")
            
            # Apply extended window logic to prevent rapid on/off switching
            final_power_decision = self._apply_extended_window_logic(agent_id, current_power_state, raw_power_decision)
            
            logger.info(f"[{self.service_id}] 🔍 DEBUG: Final decision for '{agent_id}' after extended window logic: {current_power_state} → {final_power_decision}")
            
            if final_power_decision != current_power_state:
                logger.info(f"[{self.service_id}] 🚨 ACTION NEEDED for '{agent_id}': {current_power_state} → {final_power_decision}")
                
                # Block ALL rule commands during manual override to maintain manual control
                if manual_override_active:
                    logger.info(f"[{self.service_id}] ✅ BLOCKED: ALL rule commands for '{agent_id}' - manual override active (maintaining manual state for {remaining_time:.1f}s)")
                    return
                
                # Send action command based on final decision (only when manual override is not active)
                if final_power_decision == "on":
                    self._send_action_command(agent_id, "turn_on")
                elif final_power_decision == "off":
                    self._send_action_command(agent_id, "turn_off")
            else:
                logger.debug(f"[{self.service_id}] ✅ NO ACTION: No state change needed for agent '{agent_id}' (already {current_power_state})")
                
        except Exception as e:
            logger.error(f"[{self.service_id}] Error applying rules for agent '{agent_id}': {e}", exc_info=True)

    def _apply_extended_window_logic(self, agent_id: str, current_power: str, raw_rule_decision: str) -> str:
        """
        Apply extended window logic to rule decisions.
        
        Logic:
        - OFF → ON: Start extended window, return "on"
        - During extended window:
          - Rule says "on": Extend window, return "on" 
          - Rule says "off": Continue countdown, return "on"
        - After window expires: Allow "off", return "off"
        """
        current_time = time.time()
        
        logger.info(f"[{self.service_id}] 🕰️  EXTENDED WINDOW: Evaluating for '{agent_id}' - current: {current_power}, rule: {raw_rule_decision}")
        
        with self.extended_window_lock:
            window_info = self.extended_window_agents.get(agent_id)
            
            # Case 1: OFF → ON (start new window)
            if current_power == "off" and raw_rule_decision == "on":
                self.extended_window_agents[agent_id] = {
                    "start_time": current_time,
                    "duration": self.EXTENDED_WINDOW_DURATION,
                    "last_extend_time": current_time
                }
                logger.info(f"[{self.service_id}] 🕰️  EXTENDED WINDOW: Started {self.EXTENDED_WINDOW_DURATION}s window for '{agent_id}'")
                return "on"
            
            # Case 2: No active window, follow raw decision
            if not window_info:
                logger.info(f"[{self.service_id}] 🕰️  EXTENDED WINDOW: No active window for '{agent_id}', following raw decision: {raw_rule_decision}")
                return raw_rule_decision
            
            # Case 3: Active window - check if expired
            window_start = window_info["start_time"]
            last_extend = window_info["last_extend_time"]
            time_since_last_extend = current_time - last_extend
            
            logger.info(f"[{self.service_id}] 🕰️  EXTENDED WINDOW: Active for '{agent_id}' - time since last extend: {time_since_last_extend:.1f}s / {self.EXTENDED_WINDOW_DURATION}s")
            
            # Window expired?
            if time_since_last_extend >= self.EXTENDED_WINDOW_DURATION:
                # Window expired - remove it and allow raw decision
                del self.extended_window_agents[agent_id]
                logger.info(f"[{self.service_id}] 🕰️  EXTENDED WINDOW: EXPIRED for '{agent_id}' after {time_since_last_extend:.1f}s - allowing raw decision: {raw_rule_decision}")
                return raw_rule_decision
            
            # Case 4: Active window, rule says "on" - extend window
            if raw_rule_decision == "on":
                self.extended_window_agents[agent_id]["last_extend_time"] = current_time
                remaining_time = self.EXTENDED_WINDOW_DURATION - time_since_last_extend
                logger.info(f"[{self.service_id}] 🕰️  EXTENDED WINDOW: Extended for '{agent_id}' (reset to {self.EXTENDED_WINDOW_DURATION}s)")
                return "on"
            
            # Case 5: Active window, rule says "off" - continue countdown, stay on
            else:
                remaining_time = self.EXTENDED_WINDOW_DURATION - time_since_last_extend
                logger.info(f"[{self.service_id}] 🕰️  EXTENDED WINDOW: Rule says 'off' for '{agent_id}', but in window ({remaining_time:.1f}s remaining) - staying on")
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

    def _is_action_redundant(self, agent_id: str, action_name: str, parameters: Optional[Dict[str, Any]] = None, is_manual: bool = False) -> bool:
        """Check if this action command is redundant (same as the last one sent)."""
        with self.action_command_lock:
            if agent_id not in self.last_action_commands:
                return False  # No previous command, so not redundant
            
            last_command = self.last_action_commands[agent_id]
            
            # Check if it's the same action with the same parameters
            if (last_command.get("action_name") == action_name and 
                last_command.get("parameters") == parameters):
                
                # Reduced cooldown time for faster response
                # Manual commands get shorter cooldown than automatic rules  
                cooldown_time = 0.5 if is_manual else 2.0  # 0.5s for manual, 2s for rules (increased for stability)
                time_since_last = time.time() - last_command.get("timestamp", 0)
                if time_since_last < cooldown_time:
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

    def _send_action_command(self, agent_id: str, action_name: str, parameters: Optional[Dict[str, Any]] = None, is_manual: bool = False):
        """Send an action command to a VirtualAgent (SYNCHRONOUS - Request)."""
        try:
            # Check if this action command is redundant
            if self._is_action_redundant(agent_id, action_name, parameters, is_manual):
                cooldown_time = 0.5 if is_manual else 1.0
                logger.info(f"[{self.service_id}] Skipping redundant action command '{action_name}' to agent '{agent_id}' ({cooldown_time}s cooldown active)")
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

    def set_extended_window_duration(self, duration: float) -> None:
        """Set the extended window duration for fast vs stable behavior."""
        with self.extended_window_lock:
            old_duration = self.EXTENDED_WINDOW_DURATION
            self.EXTENDED_WINDOW_DURATION = duration
            logger.info(f"[{self.service_id}] Extended window duration changed: {old_duration}s → {duration}s")
            
            # Clear existing windows when changing duration to avoid confusion
            if self.extended_window_agents:
                cleared_agents = list(self.extended_window_agents.keys())
                self.extended_window_agents.clear()
                logger.info(f"[{self.service_id}] Cleared extended windows for {len(cleared_agents)} agents due to duration change")

    def get_extended_window_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get the current extended window status for debugging purposes."""
        with self.extended_window_lock:
            window_info = self.extended_window_agents.get(agent_id)
            if not window_info:
                return None
            
            current_time = time.time()
            time_since_last_extend = current_time - window_info["last_extend_time"]
            remaining_time = self.EXTENDED_WINDOW_DURATION - time_since_last_extend
            total_window_time = current_time - window_info["start_time"]
            
            return {
                "agent_id": agent_id,
                "window_start": window_info["start_time"],
                "last_extend": window_info["last_extend_time"],
                "current_time": current_time,
                "time_since_last_extend": time_since_last_extend,
                "remaining_time": remaining_time,
                "total_window_time": total_window_time,
                "duration": self.EXTENDED_WINDOW_DURATION,
                "is_expired": time_since_last_extend >= self.EXTENDED_WINDOW_DURATION
            }

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
                # Debug logging for RDF value parsing
                if sensor_id_from_rule == "activity_detected":
                    logger.info(f"[{self.service_id}] RDF Parsing for {sensor_id_from_rule}: raw_literal='{value_rdf_node}', parsed_value='{rule_threshold_value}' ({type(rule_threshold_value)})")
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
                    # Handle boolean values explicitly
                    if isinstance(rule_threshold_value, bool):
                        # Convert agent state value to boolean for comparison
                        if isinstance(value_from_agent_state, bool):
                            result = value_from_agent_state == rule_threshold_value
                        elif isinstance(value_from_agent_state, str):
                            # Convert string representation to boolean
                            agent_bool = value_from_agent_state.lower() in ['true', '1', 'yes', 'on']
                            result = agent_bool == rule_threshold_value
                        else:
                            # Try to convert to boolean-like value
                            agent_bool = bool(value_from_agent_state)
                            result = agent_bool == rule_threshold_value
                        logger.debug(f"[{self.service_id}] Boolean comparison: agent_value='{value_from_agent_state}' ({type(value_from_agent_state)}), rule_value='{rule_threshold_value}' ({type(rule_threshold_value)}), result={result}")
                    else:
                        # Handle numeric values
                        try:
                            val_state_num = float(value_from_agent_state)
                            rule_val_num = float(rule_threshold_value)
                            result = (val_state_num == rule_val_num)
                        except (ValueError, TypeError):
                            # Fall back to string comparison
                            result = str(value_from_agent_state) == str(rule_threshold_value)
                            logger.debug(f"[{self.service_id}] String comparison: agent_value='{value_from_agent_state}', rule_value='{rule_threshold_value}', result={result}")
                
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
            
            # Log condition details for debugging (especially for boolean activity_detected)
            if sensor_id_from_rule == "activity_detected" or result:
                logger.info(f"[{self.service_id}] Condition {sensor_id_from_rule}: '{value_from_agent_state}' ({type(value_from_agent_state)}) {operator_str} '{rule_threshold_value}' ({type(rule_threshold_value)}) = {result}")
            elif not result:
                logger.debug(f"[{self.service_id}] Condition FALSE: '{value_from_agent_state}' {operator_str} '{rule_threshold_value}'")
            
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
            command_action = event.payload.get('action')  # "load", "unload", "reload", "list", "switch", "clear", "list_presets", "switch_preset"
            rule_files = event.payload.get('rule_files', [])  # list of rule file paths
            preset_name = event.payload.get('preset_name')  # preset name for easier management
            command_id = event.event.id
            
            # If preset_name is provided, use preset files
            if preset_name and preset_name in self.rule_presets:
                rule_files = self.rule_presets[preset_name]
                logger.info(f"[{self.service_id}] Using preset '{preset_name}': {rule_files}")
            
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
                    
            elif command_action == "switch":
                try:
                    # Clear existing rules and reset extended window state
                    old_files = list(self.loaded_rule_files)
                    self.clear_rules()
                    
                    # Clear extended window state when switching rules
                    with self.extended_window_lock:
                        self.extended_window_agents.clear()
                    
                    # Load new rule files
                    loaded_files = []
                    for rule_file in rule_files:
                        self.load_rules(rule_file)
                        loaded_files.append(rule_file)
                    success = True
                    message = f"Successfully switched from {old_files} to {loaded_files}"
                    logger.info(f"[{self.service_id}] RULE SWITCH: {old_files} → {loaded_files}")
                except Exception as e:
                    message = f"Error switching rules: {str(e)}"
                    
            elif command_action == "clear":
                try:
                    old_files = list(self.loaded_rule_files)
                    self.clear_rules()
                    
                    # Clear extended window state when clearing rules
                    with self.extended_window_lock:
                        self.extended_window_agents.clear()
                    
                    success = True
                    message = f"Successfully cleared {len(old_files)} rule files: {old_files}"
                    logger.info(f"[{self.service_id}] RULES CLEARED: {old_files}")
                except Exception as e:
                    message = f"Error clearing rules: {str(e)}"
                    
            elif command_action == "list":
                success = True
                message = f"Currently loaded rule files: {list(self.loaded_rule_files)}"
                
            elif command_action == "list_presets":
                success = True
                preset_info = []
                for preset, files in self.rule_presets.items():
                    preset_info.append(f"{preset}: {files}")
                message = f"Available presets:\n" + "\n".join(preset_info)
                
            elif command_action == "switch_preset":
                if not preset_name:
                    message = "preset_name is required for switch_preset action"
                elif preset_name not in self.rule_presets:
                    message = f"Unknown preset '{preset_name}'. Available presets: {list(self.rule_presets.keys())}"
                else:
                    try:
                        # Clear existing rules and reset extended window state
                        old_files = list(self.loaded_rule_files)
                        self.clear_rules()
                        
                        # Clear extended window state when switching rules
                        with self.extended_window_lock:
                            self.extended_window_agents.clear()
                        
                        # Load preset rule files
                        preset_files = self.rule_presets[preset_name]
                        loaded_files = []
                        for rule_file in preset_files:
                            self.load_rules(rule_file)
                            loaded_files.append(rule_file)
                        success = True
                        message = f"Successfully switched to preset '{preset_name}': {loaded_files}"
                        logger.info(f"[{self.service_id}] PRESET SWITCH: {old_files} → {preset_name} ({loaded_files})")
                    except Exception as e:
                        message = f"Error switching to preset '{preset_name}': {str(e)}"
                
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
            result_event = EventFactory.create_rules_command_result_event(
                command_id=command_id,
                success=success,
                message=message,
                action=action,
                loaded_files=list(self.loaded_rule_files)
            )
            
            result_topic = TopicManager.rules_management_result()
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
                parameters={**parameters, "skip_verification": True} if parameters else {"skip_verification": True},
                priority=priority
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

    def _handle_sensor_config_command(self, message_payload: str):
        """Handle sensor configuration command from dashboard and forward to virtual agent."""
        try:
            # Parse as Event structure
            event = MQTTMessage.deserialize(message_payload)
            
            if event.event.type != "sensorConfig":
                logger.error(f"[{self.service_id}] Expected sensorConfig event type, got: {event.event.type}")
                return
            
            logger.info(f"[{self.service_id}] Received sensor configuration command: {event.event.id}")
            
            # Extract command details from payload
            target_agent_id = event.payload.get('target_agent_id')
            action = event.payload.get('action')
            sensor_config = event.payload.get('sensor_config', {})
            command_id = event.event.id
            
            if not target_agent_id or not action:
                logger.error(f"[{self.service_id}] Sensor config command missing required fields: {event.payload}")
                self._publish_sensor_config_command_result(command_id, False, "Missing target_agent_id or action", target_agent_id)
                return
            
            # Check if agent exists
            if target_agent_id not in self.known_agents:
                logger.warning(f"[{self.service_id}] Sensor config command for unknown agent: {target_agent_id}")
                self._publish_sensor_config_command_result(command_id, False, f"Agent {target_agent_id} not found", target_agent_id)
                return
            
            # Forward the sensor config command to the target virtual agent
            target_topic = TopicManager.sensor_config_command(target_agent_id)
            forward_message = MQTTMessage.serialize(event)
            publish_result = self.mqtt_client.publish(target_topic, forward_message, qos=1)
            
            # Log the forwarded command
            logger.info(f"[{self.service_id}] SENSOR CONFIG COMMAND forwarded to {target_agent_id}: {action}")
            if sensor_config:
                logger.info(f"[{self.service_id}] Sensor config: {sensor_config}")
            logger.info(f"[{self.service_id}] Command ID: {command_id}")
            
            # Note: We don't send immediate result here - we wait for the virtual agent's response
            
        except json.JSONDecodeError:
            logger.error(f"[{self.service_id}] Invalid JSON in sensor config command: {message_payload}")
            self._publish_sensor_config_command_result("unknown", False, "Invalid JSON format", None)
        except Exception as e:
            logger.error(f"[{self.service_id}] Error processing sensor config command: {e}", exc_info=True)
            self._publish_sensor_config_command_result("unknown", False, f"Error: {str(e)}", None)

    def _handle_sensor_config_result(self, message_payload: str):
        """Handle sensor configuration result from virtual agent and forward to dashboard."""
        try:
            # Parse as Event structure
            event = MQTTMessage.deserialize(message_payload)
            
            if event.event.type != "sensorConfigResult":
                logger.warning(f"[{self.service_id}] Unexpected event type in sensor config result: {event.event.type}")
                return
            
            payload = event.payload
            command_id = payload.get("command_id")
            success = payload.get("success")
            message = payload.get("message")
            agent_id = payload.get("agent_id", "")
            action = payload.get("action")
            current_sensors = payload.get("current_sensors", [])
            
            logger.info(f"[{self.service_id}] Received sensor config result from agent '{agent_id}': {success} - {message}")
            
            # Forward the result back to the dashboard
            self._publish_sensor_config_command_result(command_id, success, message, agent_id, action, current_sensors)
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error handling sensor config result: {e}", exc_info=True)

    def _publish_sensor_config_command_result(self, command_id: str, success: bool, message: str, 
                                            agent_id: Optional[str], action: Optional[str] = None, 
                                            current_sensors: Optional[List[str]] = None):
        """Publish sensor configuration command result to dashboard."""
        try:
            result_event = EventFactory.create_sensor_config_command_result_event(
                command_id=command_id,
                success=success,
                message=message,
                agent_id=agent_id,
                action=action,
                current_sensors=current_sensors
            )
            
            result_topic = TopicManager.dashboard_sensor_config_result()
            message_str = MQTTMessage.serialize(result_event)
            self.mqtt_client.publish(result_topic, message_str, qos=1)
            
            logger.info(f"[{self.service_id}] Published sensor config result to dashboard: {result_topic}")
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error publishing sensor config result: {e}")

    def _handle_threshold_config_command(self, message_payload: str):
        """Handle threshold configuration command from dashboard."""
        try:
            # Parse the dashboard threshold command
            command_data = json.loads(message_payload)
            logger.debug(f"[{self.service_id}] Threshold config command data: {command_data}")
            
            # Extract command information
            event_info = command_data.get("event", {})
            payload = command_data.get("payload", {})
            command_id = event_info.get("id")
            
            agent_id = payload.get("agent_id")
            threshold_type = payload.get("threshold_type")
            config = payload.get("config", {})
            
            if not all([command_id, agent_id, threshold_type]):
                logger.error(f"[{self.service_id}] Missing required fields in threshold config command")
                self._publish_threshold_config_command_result(
                    command_id or "unknown",
                    False,
                    "Missing required fields: command_id, agent_id, or threshold_type",
                    agent_id,
                    threshold_type,
                    {}
                )
                return
            
            # Create threshold configuration event for the target agent
            threshold_event = EventFactory.create_threshold_config_event(
                agent_id=agent_id,
                threshold_type=threshold_type,
                config=config,
                source_entity_id="ContextRuleManager"
            )
            
            # Set the command ID from dashboard command
            threshold_event.event.id = command_id
            
            # Send to the specific agent
            agent_threshold_topic = TopicManager.threshold_config_command(agent_id)
            threshold_message = MQTTMessage.serialize(threshold_event)
            
            self.mqtt_client.publish(agent_threshold_topic, threshold_message, qos=1)
            
            logger.info(f"[{self.service_id}] Forwarded threshold config command to agent '{agent_id}' on topic: {agent_threshold_topic}")
            logger.debug(f"[{self.service_id}] Threshold config details: type={threshold_type}, config={config}")
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error handling threshold config command: {e}", exc_info=True)
            try:
                # Try to extract command_id for error response
                command_data = json.loads(message_payload)
                command_id = command_data.get("event", {}).get("id", "unknown")
                agent_id = command_data.get("payload", {}).get("agent_id", "unknown")
                threshold_type = command_data.get("payload", {}).get("threshold_type", "unknown")
                
                self._publish_threshold_config_command_result(
                    command_id,
                    False,
                    f"Error processing threshold config command: {str(e)}",
                    agent_id,
                    threshold_type,
                    {}
                )
            except:
                logger.error(f"[{self.service_id}] Could not send error response for threshold config command")

    def _handle_threshold_config_result(self, message_payload: str):
        """Handle threshold configuration result from virtual agent."""
        try:
            # Parse the agent's threshold config result
            event = MQTTMessage.deserialize(message_payload)
            
            if event.event.type != "thresholdConfigResult":
                logger.warning(f"[{self.service_id}] Unexpected event type in threshold config result: {event.event.type}")
                return
            
            payload = event.payload
            command_id = payload.get("command_id")
            success = payload.get("success", False)
            message = payload.get("message", "")
            agent_id = payload.get("agent_id", "")
            threshold_type = payload.get("threshold_type", "")
            current_config = payload.get("current_config", {})
            
            logger.info(f"[{self.service_id}] Received threshold config result from agent '{agent_id}': {success} - {message}")
            
            # Forward the result back to the dashboard
            self._publish_threshold_config_command_result(
                command_id,
                success,
                message,
                agent_id,
                threshold_type,
                current_config
            )
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error handling threshold config result: {e}", exc_info=True)

    def _publish_threshold_config_command_result(self, command_id: str, success: bool, message: str, 
                                               agent_id: str, threshold_type: str, current_config: Dict[str, Any]):
        """Publish threshold configuration command result to dashboard."""
        try:
            result_event = EventFactory.create_dashboard_threshold_command_result_event(
                command_id=command_id,
                success=success,
                message=message,
                agent_id=agent_id,
                threshold_type=threshold_type,
                current_config=current_config
            )
            
            result_topic = TopicManager.dashboard_threshold_result()
            message_str = MQTTMessage.serialize(result_event)
            self.mqtt_client.publish(result_topic, message_str, qos=1)
            
            logger.info(f"[{self.service_id}] Published threshold config result to dashboard: {result_topic}")
            
        except Exception as e:
            logger.error(f"[{self.service_id}] Error publishing threshold config result: {e}")

    def test_extended_window_timing(self, agent_id: str = "test_agent") -> None:
        """Manual test method to verify extended window timing logic."""
        import time
        
        logger.info(f"[{self.service_id}] TESTING: Starting extended window timing test for '{agent_id}'")
        logger.info(f"[{self.service_id}] TESTING: EXTENDED_WINDOW_DURATION = {self.EXTENDED_WINDOW_DURATION}s")
        
        # Simulate OFF → ON transition
        result1 = self._apply_extended_window_logic(agent_id, "off", "on")
        logger.info(f"[{self.service_id}] TESTING: OFF → ON result: {result1}")
        
        # Check window status immediately
        status1 = self.get_extended_window_status(agent_id)
        logger.info(f"[{self.service_id}] TESTING: Immediate window status: {status1}")
        
        # Wait 5 seconds and test "off" decision
        time.sleep(5)
        result2 = self._apply_extended_window_logic(agent_id, "on", "off")
        status2 = self.get_extended_window_status(agent_id)
        logger.info(f"[{self.service_id}] TESTING: After 5s, rule says OFF, result: {result2}")
        logger.info(f"[{self.service_id}] TESTING: After 5s window status: {status2}")
        
        # Wait another 30 seconds and test again
        time.sleep(30)
        result3 = self._apply_extended_window_logic(agent_id, "on", "off")
        status3 = self.get_extended_window_status(agent_id)
        logger.info(f"[{self.service_id}] TESTING: After 35s total, rule says OFF, result: {result3}")
        logger.info(f"[{self.service_id}] TESTING: After 35s window status: {status3}")
        
        # Wait another 30 seconds (65s total) and test expiration
        time.sleep(30)
        result4 = self._apply_extended_window_logic(agent_id, "on", "off")
        status4 = self.get_extended_window_status(agent_id)
        logger.info(f"[{self.service_id}] TESTING: After 65s total, rule says OFF, result: {result4}")
        logger.info(f"[{self.service_id}] TESTING: After 65s window status: {status4}")
        
        # Clean up test
        with self.extended_window_lock:
            if agent_id in self.extended_window_agents:
                del self.extended_window_agents[agent_id]
        
        logger.info(f"[{self.service_id}] TESTING: Extended window timing test completed") 