import logging
import threading
import time
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import queue

from .agent import Agent
from .event import EventFactory, MQTTMessage, TopicManager, SensorPayload, ActionPayload, ActionReportPayload

logger = logging.getLogger(__name__)

class VirtualAgent(Agent, ABC):
    """Base class for virtual agents that manage multiple sensors and actuators."""
    
    def __init__(self, agent_id: str, agent_type: str, mqtt_broker: str = "143.248.57.73", mqtt_port: int = 1883):
        self.agent_type = agent_type
        self.sensor_data: Dict[str, Dict[str, Any]] = {}  # Store sensor data by sensor_id
        self.sensor_agents: List[str] = []  # List of sensor IDs managed by this virtual agent
        
        # Track last published LOCAL state to avoid unnecessary updates for local state changes
        self.last_published_state: Optional[Dict[str, Any]] = None
        self.initial_state_published = False
        
        # Track processed command IDs to avoid duplicate action reports
        self.processed_command_ids: set = set()
        self.command_id_lock = threading.Lock()
        
        # Queue for publishing to avoid MQTT reentrancy issues
        self.publish_queue = queue.Queue()
        
        # Initialize the base Agent class
        super().__init__(agent_id, mqtt_broker, mqtt_port)
        
        logger.info(f"[{self.agent_id}] VirtualAgent initialized")
        
        # Start the publishing thread to handle queued publications
        self.publish_thread = threading.Thread(target=self._publish_worker, daemon=True)
        self.publish_thread.start()
        
        # Publish initial state after a short delay to ensure MQTT is connected
        threading.Timer(1.0, self._publish_initial_state).start()
    
    def _on_connect(self, client, userdata, flags, rc):
        """Override Agent's _on_connect to add virtual agent specific subscriptions."""
        # DON'T call parent's _on_connect to avoid conflicting subscriptions to "context_dist"
        # super()._on_connect(client, userdata, flags, rc)  # REMOVED to fix conflicts
        
        logger.info(f"[{self.agent_id}] VirtualAgent MQTT connected with result code {rc}")
        
        if rc == 0:
            logger.info(f"[{self.agent_id}] MQTT connected successfully, setting up subscriptions...")
            
            # Subscribe to action commands from ContextRuleManager (SYNCHRONOUS - Request)
            action_topic = TopicManager.context_to_virtual_action(self.agent_id)
            client.subscribe(action_topic, qos=1)  # Back to QoS 1 to test if QoS 2 was the issue
            logger.info(f"[{self.agent_id}] Subscribed to action topic: {action_topic}")
            
            # Subscribe to sensor data from all managed sensors (ASYNCHRONOUS)
            for sensor_id in self.sensor_agents:
                sensor_topic = TopicManager.sensor_to_virtual(sensor_id, self.agent_id)
                result = client.subscribe(sensor_topic, qos=1)  # Back to QoS 1 to test if QoS 2 was the issue
                logger.info(f"[{self.agent_id}] Subscribed to sensor topic: {sensor_topic} (result: {result})")
        else:
            logger.error(f"[{self.agent_id}] MQTT connection failed with code {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Override Agent's _on_message to handle virtual agent specific messages."""
        try:
            topic = msg.topic
            message = msg.payload.decode('utf-8')
            logger.info(f"[{self.agent_id}] DEBUG: Received MQTT message on topic: {topic}, size: {len(message)} bytes")
            
            # Check if it's an action command (SYNCHRONOUS - Request)
            action_topic = TopicManager.context_to_virtual_action(self.agent_id)
            if topic == action_topic:
                logger.info(f"[{self.agent_id}] DEBUG: Processing action command message")
                try:
                    event = MQTTMessage.deserialize(message)
                    if event.event.type == "applyAction":
                        action_payload = MQTTMessage.get_payload_as(event, ActionPayload)
                        logger.info(f"[{self.agent_id}] Received action command: {action_payload.actionName}")
                        self._handle_action_command(event, action_payload)
                    else:
                        logger.warning(f"[{self.agent_id}] Unexpected event type in action topic: {event.event.type}")
                except Exception as e:
                    logger.error(f"[{self.agent_id}] Error processing action command: {e}")
                return
            
            # Check if it's sensor data (ASYNCHRONOUS)
            sensor_message_handled = False
            for sensor_id in self.sensor_agents:
                sensor_topic = TopicManager.sensor_to_virtual(sensor_id, self.agent_id)
                if topic == sensor_topic:
                    logger.info(f"[{self.agent_id}] DEBUG: Processing sensor data message from {sensor_id}")
                    try:
                        event = MQTTMessage.deserialize(message)
                        if event.event.type == "readSensor":
                            sensor_payload = MQTTMessage.get_payload_as(event, SensorPayload)
                            logger.info(f"[{self.agent_id}] Received sensor data from {sensor_id}: {sensor_payload.value}")
                            
                            # Call update in a try-catch to see if this is where the problem occurs
                            logger.info(f"[{self.agent_id}] DEBUG: About to call _update_sensor_data")
                            self._update_sensor_data(event, sensor_payload)
                            logger.info(f"[{self.agent_id}] DEBUG: Successfully completed _update_sensor_data")
                            
                            sensor_message_handled = True
                        else:
                            logger.warning(f"[{self.agent_id}] Unexpected event type in sensor topic: {event.event.type}")
                    except Exception as e:
                        logger.error(f"[{self.agent_id}] Error processing sensor data: {e}")
                        import traceback
                        logger.error(f"[{self.agent_id}] Sensor processing traceback: {traceback.format_exc()}")
                    return
            
            if not sensor_message_handled:
                logger.info(f"[{self.agent_id}] DEBUG: Message not handled, calling parent _on_message")
                # If not handled above, call parent's _on_message
                super()._on_message(client, userdata, msg)
            
            logger.info(f"[{self.agent_id}] DEBUG: Finished processing message on topic: {topic}")
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error handling MQTT message: {e}")
            import traceback
            logger.error(f"[{self.agent_id}] Traceback: {traceback.format_exc()}")
    
    def _update_sensor_data(self, event, sensor_payload: SensorPayload):
        """Update sensor data and trigger perception update."""
        sensor_id = event.source.entityId
        
        logger.info(f"[{self.agent_id}] DEBUG: _update_sensor_data started for sensor {sensor_id}")
        
        # Track if proximity status changed (for infrared sensors)
        proximity_changed = False
        complete_state = None
        sensor_data_copy = None
        
        logger.info(f"[{self.agent_id}] DEBUG: About to acquire state_lock")
        with self.state_lock:
            logger.info(f"[{self.agent_id}] DEBUG: state_lock acquired")
            old_sensor_data = self.sensor_data.get(sensor_id, {})
            
            # Store new sensor data
            self.sensor_data[sensor_id] = {
                "sensor_type": sensor_payload.sensor_type,
                "value": sensor_payload.value,
                "unit": sensor_payload.unit,
                "metadata": sensor_payload.metadata,
                "timestamp": event.event.timestamp
            }
            
            # Check if proximity status changed for infrared sensors
            if sensor_payload.sensor_type == "infrared" and sensor_payload.metadata:
                old_proximity = old_sensor_data.get("metadata", {}).get("proximity_status") if old_sensor_data else None
                new_proximity = sensor_payload.metadata.get("proximity_status")
                
                if old_proximity != new_proximity:
                    proximity_changed = True
                    logger.info(f"[{self.agent_id}] Proximity status changed: '{old_proximity}' → '{new_proximity}'")
            
            # Prepare data for publishing while we have the lock
            complete_state = self.local_state.copy()
            for sensor_id_inner, sensor_info in self.sensor_data.items():
                complete_state[f"{sensor_id_inner}_value"] = sensor_info["value"]
                complete_state[f"{sensor_id_inner}_unit"] = sensor_info["unit"]
                if sensor_info["metadata"]:
                    for key, value in sensor_info["metadata"].items():
                        complete_state[f"{sensor_id_inner}_{key}"] = value
            sensor_data_copy = self.sensor_data.copy()
        
        logger.info(f"[{self.agent_id}] DEBUG: state_lock released")
        
        # Always trigger perception update for subclass processing
        logger.info(f"[{self.agent_id}] DEBUG: About to call _process_sensor_update")
        self._process_sensor_update(sensor_payload, sensor_id)
        logger.info(f"[{self.agent_id}] DEBUG: _process_sensor_update completed")
        
        # Always publish updateContext for sensor data (frequent updates are good for monitoring)
        logger.info(f"[{self.agent_id}] DEBUG: About to call _publish_context_update")
        self._publish_context_update_with_data(complete_state, sensor_data_copy)
        logger.info(f"[{self.agent_id}] DEBUG: _publish_context_update returned")
        
        # Log differently based on whether proximity changed
        if proximity_changed:
            logger.info(f"[{self.agent_id}] Published context update - PROXIMITY CHANGED: {sensor_payload.value}{sensor_payload.unit}")
        else:
            logger.info(f"[{self.agent_id}] Published context update - sensor reading: {sensor_payload.value}{sensor_payload.unit}")
        
        logger.info(f"[{self.agent_id}] DEBUG: _update_sensor_data completed for sensor {sensor_id}")
    
    def _handle_action_command(self, event, action_payload: ActionPayload):
        """Handle action command from ContextRuleManager (SYNCHRONOUS)."""
        try:
            command_id = event.event.id
            
            # Check if we've already processed this command ID
            with self.command_id_lock:
                if command_id in self.processed_command_ids:
                    logger.info(f"[{self.agent_id}] Skipping duplicate action command with ID: {command_id}")
                    return
                
                # Mark this command as processed
                self.processed_command_ids.add(command_id)
                
                # Clean up old command IDs (keep only last 100 to prevent memory growth)
                if len(self.processed_command_ids) > 100:
                    # Remove the oldest entries (this is a simple approach)
                    old_ids = list(self.processed_command_ids)[:50]
                    for old_id in old_ids:
                        self.processed_command_ids.discard(old_id)
            
            logger.info(f"[{self.agent_id}] Processing action command: {action_payload.actionName} (ID: {command_id})")
            result = self.execute_action(action_payload)
            
            # Create and publish actionReport event (SYNCHRONOUS - Response)
            report_event = EventFactory.create_action_report_event(
                virtual_agent_id=self.agent_id,
                command_id=command_id,  # Use the original command ID
                success=result["success"],
                message=result.get("message"),
                new_state=result.get("new_state")
            )
            
            result_topic = TopicManager.virtual_to_context_report(self.agent_id)
            result_message = MQTTMessage.serialize(report_event)
            self.mqtt_client.publish(result_topic, result_message, qos=1)  # Use QoS 1 for reliable delivery
            logger.info(f"[{self.agent_id}] Published action result: {result['success']} (ID: {command_id})")
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error executing action: {e}")
            # Send failure result
            error_event = EventFactory.create_action_report_event(
                virtual_agent_id=self.agent_id,
                command_id=event.event.id,
                success=False,
                message=str(e)
            )
            result_topic = TopicManager.virtual_to_context_report(self.agent_id)
            result_message = MQTTMessage.serialize(error_event)
            self.mqtt_client.publish(result_topic, result_message, qos=1)  # Use QoS 1 for reliable delivery
    
    def add_sensor_agent(self, sensor_id: str):
        """Add a sensor agent to be managed by this virtual agent."""
        if sensor_id not in self.sensor_agents:
            self.sensor_agents.append(sensor_id)
            logger.info(f"[{self.agent_id}] Added sensor agent: {sensor_id}")
            
            # Only subscribe if MQTT is already connected to avoid double subscription
            if self.mqtt_client.is_connected():
                sensor_topic = TopicManager.sensor_to_virtual(sensor_id, self.agent_id)
                result = self.mqtt_client.subscribe(sensor_topic, qos=1)  # Back to QoS 1 to test if QoS 2 was the issue
                logger.info(f"[{self.agent_id}] Subscribed to sensor topic: {sensor_topic} (result: {result})")
            else:
                logger.info(f"[{self.agent_id}] MQTT not connected yet, will subscribe in _on_connect")
    
    def remove_sensor_agent(self, sensor_id: str):
        """Remove a sensor agent from management."""
        if sensor_id in self.sensor_agents:
            self.sensor_agents.remove(sensor_id)
            
            # Unsubscribe from the sensor's topic
            sensor_topic = TopicManager.sensor_to_virtual(sensor_id, self.agent_id)
            self.mqtt_client.unsubscribe(sensor_topic)
            logger.info(f"[{self.agent_id}] Unsubscribed from sensor topic: {sensor_topic}")
            
            # Remove sensor data
            with self.state_lock:
                self.sensor_data.pop(sensor_id, None)
            
            logger.info(f"[{self.agent_id}] Removed sensor agent: {sensor_id}")
    
    def _process_sensor_update(self, sensor_payload: SensorPayload, sensor_id: str):
        """Process sensor data update (called when new sensor data arrives)."""
        # This method can be overridden by subclasses for specific sensor processing
        pass
    
    def _publish_worker(self):
        """Worker thread to handle queued publish operations to avoid MQTT reentrancy issues."""
        while self.running:
            try:
                # Get publish request from queue (with timeout to allow clean shutdown)
                publish_request = self.publish_queue.get(timeout=1.0)
                
                topic = publish_request['topic']
                message = publish_request['message']
                qos = publish_request.get('qos', 1)
                
                # Perform the actual publish on this separate thread
                logger.info(f"[{self.agent_id}] Publishing queued message to topic: {topic}")
                publish_result = self.mqtt_client.publish(topic, message, qos=qos)
                logger.info(f"[{self.agent_id}] Queued publish result: {publish_result}")
                
                self.publish_queue.task_done()
                
            except queue.Empty:
                # Timeout occurred, continue loop to check self.running
                continue
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error in publish worker: {e}")

    def _publish_context_update_with_data(self, complete_state: Dict[str, Any], sensor_data_copy: Dict[str, Dict[str, Any]]):
        """Publish updateContext event with provided state data (no locking needed)."""
        try:
            logger.info(f"[{self.agent_id}] DEBUG: _publish_context_update_with_data called")
            logger.info(f"[{self.agent_id}] DEBUG: complete_state = {complete_state}")
            logger.info(f"[{self.agent_id}] DEBUG: sensor_data_copy = {sensor_data_copy}")
            
            # Create updateContext event (ASYNCHRONOUS)
            context_event = EventFactory.create_context_event(
                virtual_agent_id=self.agent_id,
                agent_type=self.agent_type,
                state=complete_state,
                sensors=sensor_data_copy
            )
            
            context_topic = TopicManager.virtual_to_context(self.agent_id)
            context_message = MQTTMessage.serialize(context_event)
            
            logger.info(f"[{self.agent_id}] DEBUG: Queuing context update for topic: {context_topic}")
            
            # Queue the publish operation instead of doing it directly to avoid MQTT deadlock
            publish_request = {
                'topic': context_topic,
                'message': context_message,
                'qos': 1
            }
            self.publish_queue.put(publish_request)
            
            logger.info(f"[{self.agent_id}] Queued updateContext event for publishing")
            logger.info(f"[{self.agent_id}] DEBUG: _publish_context_update_with_data completed successfully")
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error publishing context update: {e}")
            import traceback
            logger.error(f"[{self.agent_id}] Publish context traceback: {traceback.format_exc()}")

    def _publish_context_update(self):
        """Publish updateContext event with current complete state (legacy method - acquires lock)."""
        try:
            logger.info(f"[{self.agent_id}] DEBUG: _publish_context_update called")
            with self.state_lock:
                # Combine local_state with sensor data for complete context
                complete_state = self.local_state.copy()
                logger.info(f"[{self.agent_id}] DEBUG: local_state = {self.local_state}")
                logger.info(f"[{self.agent_id}] DEBUG: sensor_data = {self.sensor_data}")
                
                # Add sensor data to state
                for sensor_id, sensor_info in self.sensor_data.items():
                    complete_state[f"{sensor_id}_value"] = sensor_info["value"]
                    complete_state[f"{sensor_id}_unit"] = sensor_info["unit"]
                    if sensor_info["metadata"]:
                        for key, value in sensor_info["metadata"].items():
                            complete_state[f"{sensor_id}_{key}"] = value
                
                logger.info(f"[{self.agent_id}] DEBUG: complete_state = {complete_state}")
                sensor_data_copy = self.sensor_data.copy()
            
            # Call the lock-free version
            self._publish_context_update_with_data(complete_state, sensor_data_copy)
                    
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error publishing context update: {e}")
            import traceback
            logger.error(f"[{self.agent_id}] Publish context traceback: {traceback.format_exc()}")
    
    def _check_and_publish_state_change(self):
        """Check if LOCAL state has changed and publish updateContext event if it has."""
        try:
            complete_state = None
            sensor_data_copy = None
            
            with self.state_lock:
                # Only check if LOCAL state changed, not sensor data
                if self.last_published_state != self.local_state:
                    # Local state changed, prepare data for publishing
                    complete_state = self.local_state.copy()
                    
                    # Add sensor data to state
                    for sensor_id, sensor_info in self.sensor_data.items():
                        complete_state[f"{sensor_id}_value"] = sensor_info["value"]
                        complete_state[f"{sensor_id}_unit"] = sensor_info["unit"]
                        if sensor_info["metadata"]:
                            for key, value in sensor_info["metadata"].items():
                                complete_state[f"{sensor_id}_{key}"] = value
                    
                    sensor_data_copy = self.sensor_data.copy()
                    
                    # Update last published state
                    self.last_published_state = self.local_state.copy()
                    
                    logger.info(f"[{self.agent_id}] Published updateContext event due to LOCAL state change")
                    logger.debug(f"[{self.agent_id}] New local state: {self.local_state}")
                else:
                    logger.debug(f"[{self.agent_id}] Local state unchanged, skipping publish")
            
            # Publish outside of the lock if state changed
            if complete_state is not None:
                self._publish_context_update_with_data(complete_state, sensor_data_copy)
                    
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error checking/publishing state change: {e}")
    
    def _publish_loop(self) -> None:
        """Override Agent's publish loop - now only used for periodic heartbeat (optional)."""
        # Instead of the base Agent's constant publishing to "context_center", 
        # we use state-change based publishing via _publish_context_update()
        while self.running:
            try:
                # Optional: Send a heartbeat every 30 seconds to indicate the agent is alive
                # For now, we'll just sleep and let state-change publishing handle updates
                time.sleep(30)  # Heartbeat interval
                
                # Optional heartbeat logic could go here if needed
                # For now, we rely purely on state-change based publishing
                
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error in publish loop: {e}")

    # Method to manually trigger state publication (e.g., when local_state changes in subclasses)
    def _trigger_state_publication(self):
        """Manually trigger state publication check. Call this when local_state is modified."""
        self._check_and_publish_state_change()
    
    # Abstract method to be implemented by subclasses
    @abstractmethod
    def execute_action(self, action_payload: ActionPayload) -> Dict[str, Any]:
        """
        Execute an action command and return the result.
        
        Args:
            action_payload: ActionPayload containing actionName and parameters
            
        Returns:
            Dict with keys: success (bool), message (str), new_state (Dict, optional)
        """
        pass

    def _publish_initial_state(self):
        """Publish the initial state of the virtual agent."""
        if not self.initial_state_published:
            # Use the lock-free version that handles its own locking
            complete_state = None
            sensor_data_copy = None
            
            with self.state_lock:
                complete_state = self.local_state.copy()
                # Add sensor data to state (though initially it will be empty)
                for sensor_id, sensor_info in self.sensor_data.items():
                    complete_state[f"{sensor_id}_value"] = sensor_info["value"]
                    complete_state[f"{sensor_id}_unit"] = sensor_info["unit"]
                    if sensor_info["metadata"]:
                        for key, value in sensor_info["metadata"].items():
                            complete_state[f"{sensor_id}_{key}"] = value
                sensor_data_copy = self.sensor_data.copy()
                self.last_published_state = self.local_state.copy()
                self.initial_state_published = True
            
            self._publish_context_update_with_data(complete_state, sensor_data_copy)
            logger.info(f"[{self.agent_id}] Published initial state") 