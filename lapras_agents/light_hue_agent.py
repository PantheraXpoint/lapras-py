import logging
import time
import sys
import os
import urllib.request
import json
import colorsys
import sys
from collections import defaultdict

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lapras_middleware.virtual_agent import VirtualAgent
from lapras_middleware.event import EventFactory, MQTTMessage, TopicManager, SensorPayload, ActionPayload, ActionReportPayload

logger = logging.getLogger(__name__)

class LightHueAgent(VirtualAgent):
    def __init__(self, agent_id: str = "hue_light", mqtt_broker: str = "143.248.57.73", mqtt_port: int = 1883, 
                 sensor_config: dict = None, transmission_interval: float = 0.5):
        super().__init__(agent_id, "hue_light", mqtt_broker, mqtt_port)
        
        logger.info(f"[{self.agent_id}] LightHueAgent initialized")

        # Default sensor configuration if none provided
        if sensor_config is None:
            sensor_config = {
                "infrared": ["infrared_1", "infrared_2"]  # Default to infrared sensors
            }
        
        self.sensor_config = sensor_config
        self.supported_sensor_types = ["infrared", "motion", "activity"]

        # Transmission rate control
        self.transmission_interval = transmission_interval  # seconds between transmissions
        self.last_transmission_time = 0.0
        self.pending_state_update = False
        
        # Initialize local state - no timing logic
        self.local_state.update({
            "power": "on",
            "proximity_status": "unknown",
            "motion_status": "unknown", 
            "activity_status": "unknown",
            "activity_detected": False,
            # Remove sensor_states - sensors section already contains all this data
            # "sensor_states": {},  # Store sensor states with timestamps
        })
        
        self.sensor_data = defaultdict(dict)  # Store sensor data with sensor_id as key
        
        # Dynamically add sensors based on configuration
        self._configure_sensors()
        
        # Subscribe to sensor configuration commands
        self._setup_sensor_config_subscription()
        
        logger.info(f"[{self.agent_id}] LightHueAgent initialization completed with sensors: {sensor_config} and transmission interval: {transmission_interval}s")
    
    def _configure_sensors(self):
        """Configure sensors based on the sensor_config."""
        total_sensors = 0
        for sensor_type, sensor_ids in self.sensor_config.items():
            if sensor_type not in self.supported_sensor_types:
                logger.warning(f"[{self.agent_id}] Unsupported sensor type: {sensor_type}")
                continue
                
            for sensor_id in sensor_ids:
                self.add_sensor_agent(sensor_id)
                total_sensors += 1
                logger.info(f"[{self.agent_id}] Added {sensor_type} sensor: {sensor_id}")
        
        logger.info(f"[{self.agent_id}] Configured {total_sensors} sensors across {len(self.sensor_config)} sensor types")
    
    def _setup_sensor_config_subscription(self):
        """Set up MQTT subscription for sensor configuration commands."""
        try:
            config_topic = f"agent/{self.agent_id}/sensorConfig"
            self.mqtt_client.subscribe(config_topic)
            self.mqtt_client.message_callback_add(config_topic, self._handle_sensor_config_command)
            logger.info(f"[{self.agent_id}] Subscribed to sensor configuration commands on: {config_topic}")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error setting up sensor config subscription: {e}")
    
    def _handle_sensor_config_command(self, client, userdata, message):
        """Handle sensor configuration commands received via MQTT."""
        try:
            import json
            from lapras_middleware.event import MQTTMessage
            
            # Deserialize the event
            event = MQTTMessage.deserialize(message.payload.decode())
            payload = event.payload
            
            if payload.get("target_agent_id") != self.agent_id:
                return  # Not for this agent
            
            action = payload.get("action")
            sensor_config = payload.get("sensor_config", {})
            
            logger.info(f"[{self.agent_id}] Received sensor config command: {action}")
            
            if action == "configure":
                self._reconfigure_sensors(sensor_config)
            elif action == "add":
                self._add_sensors(sensor_config)
            elif action == "remove":
                self._remove_sensors(sensor_config)
            elif action == "list":
                self._list_sensors()
            else:
                logger.warning(f"[{self.agent_id}] Unknown sensor config action: {action}")
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error handling sensor config command: {e}")
    
    def _reconfigure_sensors(self, new_sensor_config: dict):
        """Reconfigure all sensors with new configuration."""
        try:
            # Remove all current sensor subscriptions
            self._remove_all_sensors()
            
            # Update configuration
            self.sensor_config = new_sensor_config
            
            # Add new sensors
            self._configure_sensors()
            
            logger.info(f"[{self.agent_id}] Sensors reconfigured: {new_sensor_config}")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error reconfiguring sensors: {e}")
    
    def _add_sensors(self, sensor_config: dict):
        """Add new sensors to existing configuration."""
        try:
            for sensor_type, sensor_ids in sensor_config.items():
                if sensor_type not in self.supported_sensor_types:
                    logger.warning(f"[{self.agent_id}] Unsupported sensor type: {sensor_type}")
                    continue
                
                # Add to existing config or create new entry
                if sensor_type not in self.sensor_config:
                    self.sensor_config[sensor_type] = []
                
                for sensor_id in sensor_ids:
                    if sensor_id not in self.sensor_config[sensor_type]:
                        self.sensor_config[sensor_type].append(sensor_id)
                        self.add_sensor_agent(sensor_id)
                        logger.info(f"[{self.agent_id}] Added {sensor_type} sensor: {sensor_id}")
                    else:
                        logger.info(f"[{self.agent_id}] Sensor {sensor_id} already exists")
            
            logger.info(f"[{self.agent_id}] Sensors added. Current config: {self.sensor_config}")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error adding sensors: {e}")
    
    def _remove_sensors(self, sensor_config: dict):
        """Remove sensors from configuration."""
        try:
            for sensor_type, sensor_ids in sensor_config.items():
                if sensor_type in self.sensor_config:
                    for sensor_id in sensor_ids:
                        if sensor_id in self.sensor_config[sensor_type]:
                            self.sensor_config[sensor_type].remove(sensor_id)
                            # Note: We don't remove MQTT subscription as it might be used by other agents
                            logger.info(f"[{self.agent_id}] Removed {sensor_type} sensor: {sensor_id}")
                        else:
                            logger.warning(f"[{self.agent_id}] Sensor {sensor_id} not found in {sensor_type}")
                    
                    # Remove empty sensor types
                    if not self.sensor_config[sensor_type]:
                        del self.sensor_config[sensor_type]
            
            logger.info(f"[{self.agent_id}] Sensors removed. Current config: {self.sensor_config}")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error removing sensors: {e}")
    
    def _remove_all_sensors(self):
        """Remove all sensor subscriptions."""
        try:
            # Clear sensor configuration
            self.sensor_config = {}
            
            # Clear sensor data
            with self.state_lock:
                self.sensor_data.clear()
                # Remove sensor_states clearing since we no longer use it
                # self.local_state["sensor_states"] = {}
            
            logger.info(f"[{self.agent_id}] All sensors removed")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error removing all sensors: {e}")
    
    def _list_sensors(self):
        """List current sensor configuration."""
        try:
            total_sensors = sum(len(sensors) for sensors in self.sensor_config.values())
            logger.info(f"[{self.agent_id}] Current sensor configuration ({total_sensors} total sensors):")
            for sensor_type, sensor_ids in self.sensor_config.items():
                logger.info(f"[{self.agent_id}]   {sensor_type}: {sensor_ids}")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error listing sensors: {e}")
    
    def _process_sensor_update(self, sensor_payload: SensorPayload, sensor_id: str):
        """Process all sensor data updates immediately - no timing logic."""
        current_time = time.time()
        logger.info(f"[{self.agent_id}] Processing sensor update: {sensor_id}, type: {sensor_payload.sensor_type}, value: {sensor_payload.value}")
        
        # Process every sensor update immediately - let context manager handle timing decisions
        if sensor_payload.sensor_type == "infrared":
            self._process_infrared_sensor(sensor_payload, sensor_id, current_time)
        elif sensor_payload.sensor_type == "motion":
            self._process_motion_sensor(sensor_payload, sensor_id, current_time)
        elif sensor_payload.sensor_type == "activity":
            self._process_activity_sensor(sensor_payload, sensor_id, current_time)
        else:
            logger.warning(f"[{self.agent_id}] Unsupported sensor type: {sensor_payload.sensor_type}")
    
    def _process_infrared_sensor(self, sensor_payload: SensorPayload, sensor_id: str, current_time: float):
        """Process infrared sensor updates."""
        with self.state_lock:
            # Update sensor data
            self.sensor_data[sensor_id] = {
                "sensor_type": sensor_payload.sensor_type,
                "value": sensor_payload.value,
                "unit": sensor_payload.unit,
                "metadata": sensor_payload.metadata,
            }

            if not sensor_payload.metadata or "proximity_status" not in sensor_payload.metadata:
                logger.warning(f"[{self.agent_id}] No proximity_status in infrared sensor metadata")
                return
                
            # Update global proximity status
            proximity_detected = any(
                sensor_info.get("metadata", {}).get("proximity_status") == "near"
                for sensor_info in self.sensor_data.values()
                if sensor_info.get("sensor_type") == "infrared"
            )
            new_proximity_status = "near" if proximity_detected else "far"
            
            if self.local_state.get("proximity_status") != new_proximity_status:
                self.local_state["proximity_status"] = new_proximity_status
                logger.info(f"[{self.agent_id}] Updated proximity_status to: {new_proximity_status}")

            # Update activity_detected field for rules
            self._update_activity_detected()

            # Rate-limited state publication to context manager
            self._schedule_transmission()
    
    def _process_motion_sensor(self, sensor_payload: SensorPayload, sensor_id: str, current_time: float):
        """Process motion sensor updates."""
        with self.state_lock:
            # Update sensor data
            self.sensor_data[sensor_id] = {
                "sensor_type": sensor_payload.sensor_type,
                "value": sensor_payload.value,
                "unit": sensor_payload.unit,
                "metadata": sensor_payload.metadata,
            }

            if not sensor_payload.metadata or "motion_status" not in sensor_payload.metadata:
                logger.warning(f"[{self.agent_id}] No motion_status in motion sensor metadata")
                return
                
            # Update global motion status
            motion_detected = any(
                sensor_info.get("metadata", {}).get("motion_status") == "motion"
                for sensor_info in self.sensor_data.values()
                if sensor_info.get("sensor_type") == "motion"
            )
            new_motion_status = "motion" if motion_detected else "no_motion"
            
            if self.local_state.get("motion_status") != new_motion_status:
                self.local_state["motion_status"] = new_motion_status
                logger.info(f"[{self.agent_id}] Updated motion_status to: {new_motion_status}")

            # Update activity_detected field for rules
            self._update_activity_detected()

            # Rate-limited state publication to context manager
            self._schedule_transmission()
    
    def _process_activity_sensor(self, sensor_payload: SensorPayload, sensor_id: str, current_time: float):
        """Process activity sensor updates."""
        with self.state_lock:
            # Update sensor data
            self.sensor_data[sensor_id] = {
                "sensor_type": sensor_payload.sensor_type,
                "value": sensor_payload.value,
                "unit": sensor_payload.unit,
                "metadata": sensor_payload.metadata,
            }

            if not sensor_payload.metadata or "activity_status" not in sensor_payload.metadata:
                logger.warning(f"[{self.agent_id}] No activity_status in activity sensor metadata")
                return
                
            # Update global activity status
            activity_detected = any(
                sensor_info.get("metadata", {}).get("activity_status") == "active"
                for sensor_info in self.sensor_data.values()
                if sensor_info.get("sensor_type") == "activity"
            )
            new_activity_status = "active" if activity_detected else "inactive"
            
            if self.local_state.get("activity_status") != new_activity_status:
                self.local_state["activity_status"] = new_activity_status
                logger.info(f"[{self.agent_id}] Updated activity_status to: {new_activity_status}")

            # Update activity_detected field for rules
            self._update_activity_detected()

            # Rate-limited state publication to context manager
            self._schedule_transmission()
    
    def _update_activity_detected(self):
        """Update the activity_detected field that rules use for decisions."""
        # Check if any sensor shows activity
        activity_detected = (
            self.local_state.get("proximity_status") == "near" or
            self.local_state.get("motion_status") == "motion" or
            self.local_state.get("activity_status") == "active"
        )
        
        old_activity_detected = self.local_state.get("activity_detected", False)
        if old_activity_detected != activity_detected:
            self.local_state["activity_detected"] = activity_detected
            logger.info(f"[{self.agent_id}] Updated activity_detected: {old_activity_detected} → {activity_detected}")
    
    def _schedule_transmission(self):
        """Schedule rate-limited transmission to context manager."""
        current_time = time.time()
        
        # Mark that we have a pending state update
        self.pending_state_update = True
        
        # Check if enough time has passed since last transmission
        if current_time - self.last_transmission_time >= self.transmission_interval:
            self._transmit_to_context_manager()
        # If not enough time has passed, the periodic check will handle it
    
    def _transmit_to_context_manager(self):
        """Actually transmit state to context manager and reset pending flag."""
        if self.pending_state_update:
            self._trigger_state_publication()
            self.last_transmission_time = time.time()
            self.pending_state_update = False
            logger.debug(f"[{self.agent_id}] Transmitted state to context manager")
    
    def perception(self):
        """Internal perception logic - runs continuously."""
        current_time = time.time()
        
        # Handle rate-limited transmissions
        if (self.pending_state_update and 
            current_time - self.last_transmission_time >= self.transmission_interval):
            self._transmit_to_context_manager()
        
        # Periodic state logging
        if not hasattr(self, '_last_perception_log') or current_time - self._last_perception_log > 10:
            with self.state_lock:
                logger.info(f"[{self.agent_id}] Current state: {self.local_state}")
            self._last_perception_log = current_time
    
    def _clean_data_for_serialization(self, data):
        """Clean data to ensure it's serializable."""
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    cleaned[key] = value
                elif isinstance(value, dict):
                    cleaned[key] = self._clean_data_for_serialization(value)
                elif isinstance(value, list):
                    cleaned[key] = [self._clean_data_for_serialization(item) if isinstance(item, dict) else item for item in value]
                else:
                    # Convert other types to string
                    cleaned[key] = str(value)
            return cleaned
        return data

    def _update_sensor_data(self, event, sensor_payload: SensorPayload):
        """Update sensor data and trigger perception update."""
        sensor_id = event.source.entityId
        
        logger.info(f"[{self.agent_id}] DEBUG: _update_sensor_data started for sensor {sensor_id}")
        
        # Track if proximity status changed (for infrared sensors)
        proximity_changed = False
        complete_state = None
        sensor_data_copy = None
        
        # logger.info(f"[{self.agent_id}] DEBUG: About to acquire state_lock")
        with self.state_lock:
            # logger.info(f"[{self.agent_id}] DEBUG: state_lock acquired")
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
                assert isinstance(old_sensor_data, dict), f"[YUHENG] meta is {old_sensor_data}, sensor_payload metadata is {sensor_payload.metadata}"
                old_proximity = old_sensor_data.get("metadata", {}).get("proximity_status") if old_sensor_data else None
                new_proximity = sensor_payload.metadata.get("proximity_status")
                
                if old_proximity != new_proximity:
                    proximity_changed = True
                    logger.info(f"[{self.agent_id}] Proximity status changed: '{old_proximity}' → '{new_proximity}'")
            
            # Prepare data for publishing while we have the lock
            complete_state = self.local_state.copy()
            # Remove flattened sensor data duplication - sensors section already contains all this data
            # for sensor_id_inner, sensor_info in self.sensor_data.items():
            #     complete_state[f"{sensor_id_inner}_value"] = sensor_info["value"]
            #     complete_state[f"{sensor_id_inner}_unit"] = sensor_info["unit"]
            #     if sensor_info["metadata"]:
            #         for key, value in sensor_info["metadata"].items():
            #             complete_state[f"{sensor_id_inner}_{key}"] = value
            sensor_data_copy = self.sensor_data.copy()
        
        # logger.info(f"[{self.agent_id}] DEBUG: state_lock released")
        
        # Always trigger perception update for subclass processing
        # logger.info(f"[{self.agent_id}] DEBUG: About to call _process_sensor_update")
        self._process_sensor_update(sensor_payload, sensor_id)
        # logger.info(f"[{self.agent_id}] DEBUG: _process_sensor_update completed")
        
        # Always publish updateContext for sensor data (frequent updates are good for monitoring)
        # logger.info(f"[{self.agent_id}] DEBUG: About to call _publish_context_update")
        # self._publish_context_update_with_data(complete_state, sensor_data_copy)
        # logger.info(f"[{self.agent_id}] DEBUG: _publish_context_update returned")
        
        # Clean the data before publishing
        clean_complete_state = self._clean_data_for_serialization(complete_state)
        clean_sensor_data = self._clean_data_for_serialization(sensor_data_copy)
        
        self._publish_context_update_with_data(clean_complete_state, clean_sensor_data)
        
        # Log differently based on whether proximity changed
        if proximity_changed:
            logger.info(f"[{self.agent_id}] Published context update - PROXIMITY CHANGED: {sensor_payload.value}{sensor_payload.unit}")
        else:
            # logger.info(f"[{self.agent_id}] Published context update - sensor reading: {sensor_payload.value}{sensor_payload.unit}")
            pass
        
        # logger.info(f"[{self.agent_id}] DEBUG: _update_sensor_data completed for sensor {sensor_id}")


    def __turn_on_light(self):
        # Replace with your bridge IP and API username
        # NOTE(YH): hardcode for now
        BRIDGE_IP = "143.248.56.213:10090"
        USERNAME = "P2laHGvjzthn7Ip5-fAAIbVB9ulu9OlHWk8L7Yex"
        BASE_URL = f"http://{BRIDGE_IP}/api/{USERNAME}"
        # idx = self.agent_id.split("_")[-1]
        
        # logger.info(f"[{self.agent_id}] DEBUG: About to turn off light {idx}")
        idxs = list(range(0, 11))

        for idx in idxs:
            url = f"{BASE_URL}/lights/{idx}/state"
            data = json.dumps({"on": True}).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="PUT")
            with urllib.request.urlopen(req) as response:
                result = response.read().decode("utf-8")
                ret = {
                    "success": True,
                    "message": f"Turned on light {self.agent_id}: {result}",
                    "new_state": {
                        "power": "on"
                    }
                }
        return ret
    
    def __turn_off_light(self):
        # Replace with your bridge IP and API username
        # NOTE(YH): hardcode for now
        BRIDGE_IP = "143.248.56.213:10090"
        USERNAME = "P2laHGvjzthn7Ip5-fAAIbVB9ulu9OlHWk8L7Yex"
        BASE_URL = f"http://{BRIDGE_IP}/api/{USERNAME}"
        # idx = self.agent_id.split("_")[-1]

        # logger.info(f"[{self.agent_id}] DEBUG: About to turn off light {idx}")

        idxs = list(range(0, 11))

        for idx in idxs:
            url = f"{BASE_URL}/lights/{idx}/state"
            data = json.dumps({"on": False}).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="PUT")
            with urllib.request.urlopen(req) as response:
                result = response.read().decode("utf-8")
                ret = {
                    "success": True,
                    "message": f"Turned off light {self.agent_id}: {result}",
                    "new_state": {
                        "power": "off"
                    }
                }
        return ret

    def execute_action(self, action_payload: ActionPayload) -> dict:
        """Execute light control actions - always obey context manager commands immediately."""
        logger.info(f"[{self.agent_id}] Executing action: {action_payload.actionName}")
        
        try:            
            if action_payload.actionName == "turn_on":
                with self.state_lock:
                    self.local_state["power"] = "on"
                    new_state = self.local_state.copy()
                    result = self.__turn_on_light()
                
                logger.info(f"[{self.agent_id}] Light turned ON (commanded by context manager)")
                # Trigger state publication since local_state changed
                self._trigger_state_publication()
                
            elif action_payload.actionName == "turn_off":
                with self.state_lock:
                    self.local_state["power"] = "off"
                    new_state = self.local_state.copy()
                    result = self.__turn_off_light()
                
                logger.info(f"[{self.agent_id}] Light turned OFF (commanded by context manager)")
                # Trigger state publication since local_state changed
                self._trigger_state_publication()
                    
            return result
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error executing action: {e}")
            return {
                "success": False,
                "message": f"Error executing action: {str(e)}"
            }