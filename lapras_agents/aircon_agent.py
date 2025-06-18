import logging
import time
import sys
import os
from collections import defaultdict

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lapras_middleware.virtual_agent import VirtualAgent
from lapras_middleware.event import EventFactory, MQTTMessage, TopicManager, SensorPayload, ActionPayload, ActionReportPayload

# Import the IR controller for actual AC control
try:
    from lapras_agents.utils.test_ir_controller import AirConditionerController
except ImportError:
    AirConditionerController = None
    # Logger will be defined below - no need for duplicate declaration

logger = logging.getLogger(__name__)

# Log warning if IR controller is not available
if AirConditionerController is None:
    logger.warning("AirConditionerController not available - using mock implementation")

class AirconAgent(VirtualAgent):
    def __init__(self, agent_id: str = "aircon", mqtt_broker: str = "143.248.57.73", mqtt_port: int = 1883, 
                 sensor_config: dict = None, transmission_interval: float = 0.5, phidget_serial: int = -1):
        
        # Initialize attributes that might be accessed by perception thread first
        self.transmission_interval = transmission_interval  # seconds between transmissions
        self.last_transmission_time = 0.0
        self.pending_state_update = False
        
        super().__init__(agent_id, "aircon", mqtt_broker, mqtt_port)
        
        logger.info(f"[{self.agent_id}] AirconAgent initialized")

        # Default sensor configuration if none provided
        if sensor_config is None:
            sensor_config = {
                "infrared": ["infrared_1"],  # Default to infrared sensor
            }
        
        self.sensor_config = sensor_config
        self.supported_sensor_types = ["infrared", "motion", "activity"]
        
        # Initialize IR controller for actual AC control first
        self.ir_controller = None
        self.phidget_serial = phidget_serial
        self._initialize_ir_controller()
        
        # Ensure aircon starts in known "off" state by sending turn off command
        initial_power_state = self.__ensure_aircon_off_on_startup()
        
        # Initialize local state with known state
        self.local_state.update({
            "power": initial_power_state,
            "temperature": 25,  # Default temperature setting
            "mode": "auto",     # auto, cool, heat, fan
            "proximity_status": "unknown",
            "motion_status": "unknown", 
            "activity_status": "unknown",
            "activity_detected": False,
        })
        
        logger.info(f"[{self.agent_id}] Initialized with ensured aircon state: {initial_power_state}")
        
        self.sensor_data = defaultdict(dict)  # Store sensor data with sensor_id as key
        
        # Dynamically add sensors based on configuration
        self._configure_sensors()
        
        logger.info(f"[{self.agent_id}] AirconAgent initialization completed with sensors: {sensor_config} and transmission interval: {transmission_interval}s")

        # Publish initial state to context manager
        self._trigger_initial_state_publication()
    
    def _initialize_ir_controller(self):
        """Initialize the IR controller for AC control."""
        try:
            if AirConditionerController:
                self.ir_controller = AirConditionerController(self.phidget_serial)
                logger.info(f"[{self.agent_id}] IR controller initialized with serial: {self.phidget_serial}")
            else:
                logger.warning(f"[{self.agent_id}] IR controller not available - using mock mode")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to initialize IR controller: {e}")
            self.ir_controller = None
    
    def __ensure_aircon_off_on_startup(self):
        """Ensure the aircon starts in known "off" state by sending turn off command."""
        try:
            logger.info(f"[{self.agent_id}] Ensuring aircon is OFF at startup...")
            
            # Send turn off command to ensure aircon is off
            result = self.__turn_off_aircon()
            
            if result["success"]:
                logger.info(f"[{self.agent_id}] Aircon turned OFF successfully during initialization")
                return "off"
            else:
                logger.warning(f"[{self.agent_id}] Failed to turn off aircon during initialization: {result.get('message')}")
                return "off"  # Still assume off state even if command failed
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error ensuring aircon OFF state during initialization: {e}")
            return "off"  # Default to off state if error occurs
    
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
        
        with self.state_lock:
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
        
        # Always trigger perception update for subclass processing
        self._process_sensor_update(sensor_payload, sensor_id)
        
        # Clean the data before publishing
        clean_complete_state = self._clean_data_for_serialization(complete_state)
        clean_sensor_data = self._clean_data_for_serialization(sensor_data_copy)
        
        self._publish_context_update_with_data(clean_complete_state, clean_sensor_data)
        
        # Log differently based on whether proximity changed
        if proximity_changed:
            logger.info(f"[{self.agent_id}] Published context update - PROXIMITY CHANGED: {sensor_payload.value}{sensor_payload.unit}")
        else:
            pass

    def __turn_on_aircon(self):
        """Turn on the air conditioner using IR controller."""
        try:
            if self.ir_controller:
                success = self.ir_controller.turn_on()
                if success:
                    return {
                        "success": True,
                        "message": f"Turned on aircon {self.agent_id} via IR controller",
                        "new_state": {
                            "power": "on"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to turn on aircon {self.agent_id} via IR controller"
                    }
            else:
                # Mock mode - just return success
                logger.info(f"[{self.agent_id}] Mock: Turning on aircon")
                return {
                    "success": True,
                    "message": f"Turned on aircon {self.agent_id} (mock mode)",
                    "new_state": {
                        "power": "on"
                    }
                }
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error turning on aircon: {e}")
            return {
                "success": False,
                "message": f"Error turning on aircon: {str(e)}"
            }
    
    def __turn_off_aircon(self):
        """Turn off the air conditioner using IR controller."""
        try:
            if self.ir_controller:
                success = self.ir_controller.turn_off()
                if success:
                    return {
                        "success": True,
                        "message": f"Turned off aircon {self.agent_id} via IR controller",
                        "new_state": {
                            "power": "off"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to turn off aircon {self.agent_id} via IR controller"
                    }
            else:
                # Mock mode - just return success
                logger.info(f"[{self.agent_id}] Mock: Turning off aircon")
                return {
                    "success": True,
                    "message": f"Turned off aircon {self.agent_id} (mock mode)",
                    "new_state": {
                        "power": "off"
                    }
                }
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error turning off aircon: {e}")
            return {
                "success": False,
                "message": f"Error turning off aircon: {str(e)}"
            }
    
    def __temp_up_aircon(self):
        """Increase temperature using IR controller."""
        try:
            if self.ir_controller:
                success = self.ir_controller.temp_up()
                new_temp = self.local_state.get("temperature", 25) + 1
                if success:
                    return {
                        "success": True,
                        "message": f"Increased temperature of aircon {self.agent_id} via IR controller",
                        "new_state": {
                            "temperature": new_temp
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to increase temperature of aircon {self.agent_id} via IR controller"
                    }
            else:
                # Mock mode - just return success
                new_temp = self.local_state.get("temperature", 25) + 1
                logger.info(f"[{self.agent_id}] Mock: Increasing temperature to {new_temp}")
                return {
                    "success": True,
                    "message": f"Increased temperature of aircon {self.agent_id} to {new_temp}°C (mock mode)",
                    "new_state": {
                        "temperature": new_temp
                    }
                }
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error increasing temperature: {e}")
            return {
                "success": False,
                "message": f"Error increasing temperature: {str(e)}"
            }
    
    def __temp_down_aircon(self):
        """Decrease temperature using IR controller."""
        try:
            if self.ir_controller:
                success = self.ir_controller.temp_down()
                new_temp = self.local_state.get("temperature", 25) - 1
                if success:
                    return {
                        "success": True,
                        "message": f"Decreased temperature of aircon {self.agent_id} via IR controller",
                        "new_state": {
                            "temperature": new_temp
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to decrease temperature of aircon {self.agent_id} via IR controller"
                    }
            else:
                # Mock mode - just return success
                new_temp = self.local_state.get("temperature", 25) - 1
                logger.info(f"[{self.agent_id}] Mock: Decreasing temperature to {new_temp}")
                return {
                    "success": True,
                    "message": f"Decreased temperature of aircon {self.agent_id} to {new_temp}°C (mock mode)",
                    "new_state": {
                        "temperature": new_temp
                    }
                }
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error decreasing temperature: {e}")
            return {
                "success": False,
                "message": f"Error decreasing temperature: {str(e)}"
            }

    def execute_action(self, action_payload: ActionPayload) -> dict:
        """Execute aircon control actions with fast response (no verification)."""
        logger.info(f"[{self.agent_id}] Executing action: {action_payload.actionName}")
        
        # Check if verification should be skipped for faster response
        # For manual commands or when explicitly disabled
        skip_verification = action_payload.parameters and action_payload.parameters.get("skip_verification", False)
        
        try:            
            if action_payload.actionName == "turn_on":
                # Execute the physical action
                result = self.__turn_on_aircon()
                
                if skip_verification:
                    # Skip verification for faster response
                    logger.info(f"[{self.agent_id}] Turn ON command executed (verification skipped for speed)")
                    with self.state_lock:
                        self.local_state["power"] = "on"
                        result["new_state"]["power"] = "on"
                        result["message"] = "Turn ON: executed (verification skipped)"
                else:
                    # Update local state immediately without verification (aircon doesn't have verification)
                    logger.info(f"[{self.agent_id}] Turn ON command executed")
                    with self.state_lock:
                        self.local_state["power"] = "on"
                        result["new_state"]["power"] = "on"
                
                # Always trigger state publication
                self._trigger_state_publication()
                
            elif action_payload.actionName == "turn_off":
                # Execute the physical action
                result = self.__turn_off_aircon()
                
                if skip_verification:
                    # Skip verification for faster response
                    logger.info(f"[{self.agent_id}] Turn OFF command executed (verification skipped for speed)")
                    with self.state_lock:
                        self.local_state["power"] = "off"
                        result["new_state"]["power"] = "off"
                        result["message"] = "Turn OFF: executed (verification skipped)"
                else:
                    # Update local state immediately without verification (aircon doesn't have verification)
                    logger.info(f"[{self.agent_id}] Turn OFF command executed")
                    with self.state_lock:
                        self.local_state["power"] = "off"
                        result["new_state"]["power"] = "off"
                
                # Always trigger state publication
                self._trigger_state_publication()
                
            elif action_payload.actionName == "temp_up":
                with self.state_lock:
                    old_temp = self.local_state.get("temperature", 25)
                    self.local_state["temperature"] = old_temp + 1
                    new_state = self.local_state.copy()
                    result = self.__temp_up_aircon()
                
                logger.info(f"[{self.agent_id}] Aircon temperature increased (commanded by context manager)")
                # Trigger state publication since local_state changed
                self._trigger_state_publication()
                
            elif action_payload.actionName == "temp_down":
                with self.state_lock:
                    old_temp = self.local_state.get("temperature", 25)
                    self.local_state["temperature"] = old_temp - 1
                    new_state = self.local_state.copy()
                    result = self.__temp_down_aircon()
                
                logger.info(f"[{self.agent_id}] Aircon temperature decreased (commanded by context manager)")
                # Trigger state publication since local_state changed
                self._trigger_state_publication()
                
            elif action_payload.actionName == "set_temperature":
                if action_payload.parameters and "temperature" in action_payload.parameters:
                    temp = action_payload.parameters["temperature"]
                    with self.state_lock:
                        self.local_state["temperature"] = temp
                        new_state = self.local_state.copy()
                    result = {
                        "success": True,
                        "message": f"Temperature set to {temp}°C",
                        "new_state": {"temperature": temp}
                    }
                    logger.info(f"[{self.agent_id}] Temperature set to {temp}°C")
                    # Trigger state publication since local_state changed
                    self._trigger_state_publication()
                else:
                    result = {
                        "success": False,
                        "message": "Temperature parameter missing"
                    }
                    
            elif action_payload.actionName == "set_mode":
                if action_payload.parameters and "mode" in action_payload.parameters:
                    mode = action_payload.parameters["mode"]
                    if mode in ["auto", "cool", "heat", "fan"]:
                        with self.state_lock:
                            self.local_state["mode"] = mode
                            new_state = self.local_state.copy()
                        result = {
                            "success": True,
                            "message": f"Mode set to {mode}",
                            "new_state": {"mode": mode}
                        }
                        logger.info(f"[{self.agent_id}] Mode set to {mode}")
                        # Trigger state publication since local_state changed
                        self._trigger_state_publication()
                    else:
                        result = {
                            "success": False,
                            "message": f"Invalid mode: {mode}. Valid modes: auto, cool, heat, fan"
                        }
                else:
                    result = {
                        "success": False,
                        "message": "Mode parameter missing"
                    }
                    
            else:
                result = {
                    "success": False,
                    "message": f"Unknown action: {action_payload.actionName}",
                    "new_state": {}
                }
                logger.warning(f"[{self.agent_id}] Unknown action: {action_payload.actionName}")
            
            return result
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error executing action: {e}")
            return {
                "success": False,
                "message": f"Error executing action: {str(e)}"
            }
    
    def stop(self):
        """Stop the aircon agent and clean up IR controller."""
        if self.ir_controller:
            try:
                self.ir_controller.close()
                logger.info(f"[{self.agent_id}] IR controller closed")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error closing IR controller: {e}")
        
        super().stop()

    def _trigger_initial_state_publication(self):
        """Trigger initial state publication to context manager after initialization."""
        try:
            # Small delay to ensure MQTT connection is ready
            import time
            time.sleep(0.5)
            
            # Trigger state publication with actual aircon state
            self._trigger_state_publication()
            logger.info(f"[{self.agent_id}] Initial state published to context manager: power={self.local_state.get('power')}")
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error publishing initial state: {e}")

    def refresh_aircon_state(self):
        """Manually refresh the aircon state and update local state."""
        try:
            logger.info(f"[{self.agent_id}] Manually refreshing aircon state...")
            
            with self.state_lock:
                old_power_state = self.local_state.get("power")
                # Since we don't have verification anymore, just log current state
                current_power_state = self.local_state.get("power")
                
                if old_power_state == current_power_state:
                    logger.debug(f"[{self.agent_id}] Aircon state refresh: no change ({current_power_state})")
                    return False  # No state change
                else:
                    logger.info(f"[{self.agent_id}] Aircon state refreshed: {old_power_state} → {current_power_state}")
                    # Trigger state publication since state changed
                    self._trigger_state_publication()
                    return True  # State changed
                    
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error refreshing aircon state: {e}")
            return False
