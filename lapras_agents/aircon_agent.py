import logging
import time
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lapras_middleware.virtual_agent import VirtualAgent
from lapras_middleware.event import ActionPayload, SensorPayload

logger = logging.getLogger(__name__)

class AirconAgent(VirtualAgent):
    def __init__(self, agent_id: str = "aircon", mqtt_broker: str = "143.248.57.73", mqtt_port: int = 1883):
        super().__init__(agent_id, "aircon", mqtt_broker, mqtt_port)
        
        logger.info(f"[{self.agent_id}] AirconAgent initialized")
        
        # Initialize state
        with self.state_lock:
            self.local_state.update({
                "power": "off",
                "temperature": 25,  # Default temperature setting
                "mode": "auto",     # auto, cool, heat, fan
                "proximity_status": "unknown"
            })
        
        # Add infrared sensor to this virtual agent
        self.add_sensor_agent("infrared_1")
        
        logger.info(f"[{self.agent_id}] AirconAgent initialization completed")

    def _process_sensor_update(self, sensor_payload: SensorPayload, sensor_id: str):
        """Process sensor data updates from managed sensors."""
        if sensor_payload.sensor_type == "infrared":
            # DEBUG: Log all received sensor readings to debug the issue
            logger.info(f"[{self.agent_id}] DEBUG: Received IR sensor reading: distance={sensor_payload.value}{sensor_payload.unit}, metadata={sensor_payload.metadata}")
            
            # Update proximity status based on infrared sensor
            if sensor_payload.metadata and "proximity_status" in sensor_payload.metadata:
                old_proximity = None
                old_distance = None
                with self.state_lock:
                    old_proximity = self.local_state.get("proximity_status")
                    old_distance = self.local_state.get("distance")
                    self.local_state["proximity_status"] = sensor_payload.metadata["proximity_status"]
                    self.local_state["distance"] = sensor_payload.value
                
                # Only log and trigger publication if something actually changed
                if (old_proximity != sensor_payload.metadata["proximity_status"] or 
                    old_distance != sensor_payload.value):
                    logger.info(f"[{self.agent_id}] Updated from IR sensor: distance={sensor_payload.value}{sensor_payload.unit}, proximity={sensor_payload.metadata['proximity_status']}")
                    # Trigger state publication since local_state changed
                    self._trigger_state_publication()
                else:
                    logger.debug(f"[{self.agent_id}] IR sensor data unchanged: distance={sensor_payload.value}{sensor_payload.unit}, proximity={sensor_payload.metadata['proximity_status']}")

    def perception(self):
        """Internal perception logic - runs continuously."""
        # This can be used for internal state management or decision making
        # For now, we'll just log periodically
        current_time = time.time()
        if not hasattr(self, '_last_perception_log') or current_time - self._last_perception_log > 10:
            with self.state_lock:
                logger.info(f"[{self.agent_id}] Current state: {self.local_state}")
            self._last_perception_log = current_time

    def execute_action(self, action_payload: ActionPayload) -> dict:
        """Execute aircon control actions."""
        logger.info(f"[{self.agent_id}] Executing action: {action_payload.actionName}")
        
        try:
            success = False
            message = ""
            new_state = None
            
            if action_payload.actionName == "turn_on":
                with self.state_lock:
                    self.local_state["power"] = "on"
                    new_state = self.local_state.copy()
                success = True
                message = "Aircon turned on successfully"
                logger.info(f"[{self.agent_id}] Aircon turned ON")
                # Trigger state publication since local_state changed
                self._trigger_state_publication()
                
            elif action_payload.actionName == "turn_off":
                with self.state_lock:
                    self.local_state["power"] = "off"
                    new_state = self.local_state.copy()
                success = True
                message = "Aircon turned off successfully"
                logger.info(f"[{self.agent_id}] Aircon turned OFF")
                # Trigger state publication since local_state changed
                self._trigger_state_publication()
                
            elif action_payload.actionName == "set_temperature":
                if action_payload.parameters and "temperature" in action_payload.parameters:
                    temp = action_payload.parameters["temperature"]
                    with self.state_lock:
                        self.local_state["temperature"] = temp
                        new_state = self.local_state.copy()
                    success = True
                    message = f"Temperature set to {temp}°C"
                    logger.info(f"[{self.agent_id}] Temperature set to {temp}°C")
                    # Trigger state publication since local_state changed
                    self._trigger_state_publication()
                else:
                    success = False
                    message = "Temperature parameter missing"
                    
            elif action_payload.actionName == "set_mode":
                if action_payload.parameters and "mode" in action_payload.parameters:
                    mode = action_payload.parameters["mode"]
                    if mode in ["auto", "cool", "heat", "fan"]:
                        with self.state_lock:
                            self.local_state["mode"] = mode
                            new_state = self.local_state.copy()
                        success = True
                        message = f"Mode set to {mode}"
                        logger.info(f"[{self.agent_id}] Mode set to {mode}")
                        # Trigger state publication since local_state changed
                        self._trigger_state_publication()
                    else:
                        success = False
                        message = f"Invalid mode: {mode}. Valid modes: auto, cool, heat, fan"
                else:
                    success = False
                    message = "Mode parameter missing"
                    
            else:
                success = False
                message = f"Unknown action type: {action_payload.actionName}"
                logger.warning(f"[{self.agent_id}] Unknown action type: {action_payload.actionName}")
            
            return {
                "success": success,
                "message": message,
                "new_state": new_state
            }
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error executing action: {e}")
            return {
                "success": False,
                "message": f"Error executing action: {str(e)}"
            }
