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
                 sensor_config: dict = None, transmission_interval: float = 0.5, 
                 light_threshold: float = 50.0):
        super().__init__(agent_id, "hue_light", mqtt_broker, mqtt_port)
        
        logger.info(f"[{self.agent_id}] LightHueAgent initialized")

        # Default sensor configuration if none provided
        if sensor_config is None:
            sensor_config = {
                "infrared": ["infrared_1", "infrared_2"],  # Default to infrared sensors
                "light": ["light_1"]  # Add light sensor support
            }
        
        self.sensor_config = sensor_config
        self.supported_sensor_types = ["infrared", "motion", "activity", "light"]

        # Light sensor configuration for bright/dark classification
        self.light_threshold = light_threshold  # lux threshold: below = dark, above = bright

        # Transmission rate control
        self.transmission_interval = transmission_interval  # seconds between transmissions
        self.last_transmission_time = 0.0
        self.pending_state_update = False
        
        # Initialize local state - check actual light status first
        actual_power_state = self.__check_current_light_state()
        self.local_state.update({
            "power": actual_power_state,
            "proximity_status": "unknown",
            "motion_status": "unknown", 
            "activity_status": "unknown",
            "activity_detected": False,
            "light_status": "unknown",  # bright or dark
        })
        
        logger.info(f"[{self.agent_id}] Initialized with actual light state: {actual_power_state}")
        
        self.sensor_data = defaultdict(dict)  # Store sensor data with sensor_id as key
        
        # Dynamically add sensors based on configuration
        self._configure_sensors()
        
        logger.info(f"[{self.agent_id}] LightHueAgent initialization completed with sensors: {sensor_config}, transmission interval: {transmission_interval}s, light threshold: {light_threshold} lux")

        # Publish initial state to context manager
        self._trigger_initial_state_publication()
    
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
    
    def _update_sensor_config(self, new_sensor_config: dict, action: str = "configure"):
        """Update subclass-specific sensor configuration (called by base class)."""
        try:
            if action == "configure":
                # Replace entire configuration
                self.sensor_config = new_sensor_config
            elif action == "add":
                # Add to existing configuration
                for sensor_type, sensor_ids in new_sensor_config.items():
                    if sensor_type not in self.sensor_config:
                        self.sensor_config[sensor_type] = []
                    for sensor_id in sensor_ids:
                        if sensor_id not in self.sensor_config[sensor_type]:
                            self.sensor_config[sensor_type].append(sensor_id)
            elif action == "remove":
                # Remove from existing configuration
                for sensor_type, sensor_ids in new_sensor_config.items():
                    if sensor_type in self.sensor_config:
                        for sensor_id in sensor_ids:
                            if sensor_id in self.sensor_config[sensor_type]:
                                self.sensor_config[sensor_type].remove(sensor_id)
                        # Remove empty sensor types
                        if not self.sensor_config[sensor_type]:
                            del self.sensor_config[sensor_type]
            
            logger.info(f"[{self.agent_id}] Updated sensor configuration: {self.sensor_config}")
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error updating sensor configuration: {e}")
    
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
        elif sensor_payload.sensor_type == "light":
            self._process_light_sensor(sensor_payload, sensor_id, current_time)
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
    
    def _process_light_sensor(self, sensor_payload: SensorPayload, sensor_id: str, current_time: float):
        """Process light sensor updates and convert lux to bright/dark terms."""
        with self.state_lock:
            # Update sensor data
            self.sensor_data[sensor_id] = {
                "sensor_type": sensor_payload.sensor_type,
                "value": sensor_payload.value,
                "unit": sensor_payload.unit,
                "metadata": sensor_payload.metadata,
            }

            # Convert lux value to bright/dark based on threshold
            try:
                lux_value = float(sensor_payload.value)
                light_status = "bright" if lux_value >= self.light_threshold else "dark"
                
                if self.local_state.get("light_status") != light_status:
                    self.local_state["light_status"] = light_status
                    logger.info(f"[{self.agent_id}] Updated light_status to: {light_status} (lux: {lux_value})")
                
            except (ValueError, TypeError) as e:
                logger.warning(f"[{self.agent_id}] Could not convert light sensor value to float: {sensor_payload.value}, error: {e}")
                return

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

    def __check_current_light_state(self):
        """Check the current state of the lights from the Hue bridge."""
        # Replace with your bridge IP and API username
        # NOTE(YH): hardcode for now
        BRIDGE_IP = "143.248.55.137:10090"
        USERNAME = "P2laHGvjzthn7Ip5-fAAIbVB9ulu9OlHWk8L7Yex"
        BASE_URL = f"http://{BRIDGE_IP}/api/{USERNAME}"
        
        try:
            # Check the state of all lights (0-10)
            idxs = list(range(0, 11))
            lights_on = 0
            total_lights = 0
            
            for idx in idxs:
                try:
                    url = f"{BASE_URL}/lights/{idx}"
                    req = urllib.request.Request(url, method="GET")
                    with urllib.request.urlopen(req) as response:
                        result = response.read().decode("utf-8")
                        light_data = json.loads(result)
                        
                        # Check if the light exists and is on
                        if "state" in light_data and "on" in light_data["state"]:
                            total_lights += 1
                            if light_data["state"]["on"]:
                                lights_on += 1
                            logger.debug(f"[{self.agent_id}] Light {idx}: {'on' if light_data['state']['on'] else 'off'}")
                        else:
                            logger.debug(f"[{self.agent_id}] Light {idx}: not found or invalid response")
                            
                except Exception as e:
                    logger.debug(f"[{self.agent_id}] Failed to check light {idx}: {e}")
                    continue
            
            # Determine overall state based on majority of lights
            if total_lights == 0:
                logger.warning(f"[{self.agent_id}] No lights found, defaulting to 'off'")
                return "off"
            
            # If more than half the lights are on, consider the system "on"
            if lights_on > total_lights / 2:
                logger.info(f"[{self.agent_id}] Light state check: {lights_on}/{total_lights} lights on -> 'on'")
                return "on"
            else:
                logger.info(f"[{self.agent_id}] Light state check: {lights_on}/{total_lights} lights on -> 'off'")
                return "off"
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error checking current light state: {e}")
            # Default to "off" if we can't determine the state
            logger.warning(f"[{self.agent_id}] Failed to check light state, defaulting to 'off'")
            return "off"

    def __turn_on_light(self):
        # Replace with your bridge IP and API username
        # NOTE(YH): hardcode for now
        BRIDGE_IP = "143.248.55.137:10090"
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
        BRIDGE_IP = "143.248.55.137:10090"
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

    def __verify_action_result(self, expected_state: str, max_retries: int = 2, retry_delay: float = 0.5) -> tuple:
        """
        Verify that the light state matches the expected state after an action.
        
        Args:
            expected_state: Expected power state ("on" or "off")
            max_retries: Maximum number of verification attempts (reduced for faster response)
            retry_delay: Delay between verification attempts in seconds (reduced for faster response)
            
        Returns:
            Tuple of (success: bool, actual_state: str, message: str)
        """
        for attempt in range(max_retries):
            try:
                time.sleep(retry_delay)  # Allow time for lights to respond
                actual_state = self.__check_current_light_state()
                
                logger.debug(f"[{self.agent_id}] Verification attempt {attempt + 1}/{max_retries}: expected='{expected_state}', actual='{actual_state}'")
                
                if actual_state == expected_state:
                    return True, actual_state, f"Verification successful after {attempt + 1} attempt(s)"
                
                if attempt < max_retries - 1:
                    logger.debug(f"[{self.agent_id}] Verification attempt {attempt + 1} failed, retrying...")
                    
            except Exception as e:
                logger.warning(f"[{self.agent_id}] Verification attempt {attempt + 1} failed with error: {e}")
                if attempt < max_retries - 1:
                    logger.debug(f"[{self.agent_id}] Retrying verification...")
                    
        return False, actual_state, f"Verification failed after {max_retries} attempts: expected '{expected_state}', got '{actual_state}'"

    def execute_action(self, action_payload: ActionPayload) -> dict:
        """Execute light control actions and verify actual state before reporting back."""
        logger.info(f"[{self.agent_id}] Executing action: {action_payload.actionName}")
        
        # Check if verification should be skipped for faster response
        # For manual commands or when explicitly disabled
        skip_verification = action_payload.parameters and action_payload.parameters.get("skip_verification", False)
        
        try:            
            if action_payload.actionName == "turn_on":
                # Execute the physical action first
                result = self.__turn_on_light()
                
                if skip_verification:
                    # Skip verification for faster response
                    logger.info(f"[{self.agent_id}] Turn ON command executed (verification skipped for speed)")
                    with self.state_lock:
                        self.local_state["power"] = "on"
                        result["new_state"]["power"] = "on"
                        result["message"] = "Turn ON: executed (verification skipped)"
                else:
                    # Verify actual light state with retry logic
                    verification_success, actual_state, verification_message = self.__verify_action_result("on")
                    
                    logger.info(f"[{self.agent_id}] Turn ON command executed, {verification_message}")
                    
                    # Update local state based on verified actual state
                    with self.state_lock:
                        old_power_state = self.local_state.get("power")
                        self.local_state["power"] = actual_state
                        
                        # Update result with verified state
                        result["new_state"]["power"] = actual_state
                        result["success"] = verification_success
                        result["message"] = f"Turn ON: {verification_message}"
                        
                        if verification_success:
                            logger.info(f"[{self.agent_id}] Light turned ON successfully (verified)")
                        else:
                            logger.warning(f"[{self.agent_id}] Light turn ON verification failed: {verification_message}")
                
                # Always trigger state publication with verified state
                self._trigger_state_publication()
                
            elif action_payload.actionName == "turn_off":
                # Execute the physical action first
                result = self.__turn_off_light()
                
                if skip_verification:
                    # Skip verification for faster response
                    logger.info(f"[{self.agent_id}] Turn OFF command executed (verification skipped for speed)")
                    with self.state_lock:
                        self.local_state["power"] = "off"
                        result["new_state"]["power"] = "off"
                        result["message"] = "Turn OFF: executed (verification skipped)"
                else:
                    # Verify actual light state with retry logic
                    verification_success, actual_state, verification_message = self.__verify_action_result("off")
                    
                    logger.info(f"[{self.agent_id}] Turn OFF command executed, {verification_message}")
                    
                    # Update local state based on verified actual state
                    with self.state_lock:
                        old_power_state = self.local_state.get("power")
                        self.local_state["power"] = actual_state
                        
                        # Update result with verified state
                        result["new_state"]["power"] = actual_state
                        result["success"] = verification_success
                        result["message"] = f"Turn OFF: {verification_message}"
                        
                        if verification_success:
                            logger.info(f"[{self.agent_id}] Light turned OFF successfully (verified)")
                        else:
                            logger.warning(f"[{self.agent_id}] Light turn OFF verification failed: {verification_message}")
                
                # Always trigger state publication with verified state
                self._trigger_state_publication()
                
            else:
                result = {
                    "success": False,
                    "message": f"Unknown action: {action_payload.actionName}",
                    "new_state": {}
                }
                    
            return result
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error executing action: {e}")
            return {
                "success": False,
                "message": f"Error executing action: {str(e)}"
            }

    def _trigger_initial_state_publication(self):
        """Trigger initial state publication to context manager after initialization."""
        try:
            # Small delay to ensure MQTT connection is ready
            import time
            time.sleep(0.5)
            
            # Trigger state publication with actual light state
            self._trigger_state_publication()
            logger.info(f"[{self.agent_id}] Initial state published to context manager: power={self.local_state.get('power')}")
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error publishing initial state: {e}")

    def refresh_light_state(self):
        """Manually refresh the light state from the Hue bridge and update local state."""
        try:
            current_power_state = self.__check_current_light_state()
            
            with self.state_lock:
                old_power_state = self.local_state.get("power")
                self.local_state["power"] = current_power_state
                
                if old_power_state != current_power_state:
                    logger.info(f"[{self.agent_id}] Light state refreshed: {old_power_state} → {current_power_state}")
                    # Trigger state publication since state changed
                    self._trigger_state_publication()
                    return True  # State changed
                else:
                    logger.debug(f"[{self.agent_id}] Light state refresh: no change ({current_power_state})")
                    return False  # No state change
                    
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error refreshing light state: {e}")
            return False