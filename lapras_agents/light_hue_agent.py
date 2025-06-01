import logging
import time
import sys
import os
import urllib.request
import json
import colorsys
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lapras_middleware.virtual_agent import VirtualAgent
from lapras_middleware.event import EventFactory, MQTTMessage, TopicManager, SensorPayload, ActionPayload, ActionReportPayload

logger = logging.getLogger(__name__)

class LightHueAgent(VirtualAgent):
    def __init__(self, agent_id: str = "none", mqtt_broker: str = "143.248.57.73", mqtt_port: int = 1883):
        super().__init__(agent_id, "hue_light", mqtt_broker, mqtt_port)
        
        logger.info(f"[{self.agent_id}] LightHueAgent initialized")

        with self.state_lock:
            self.local_state.update({
                "power": "off",
                "proximity_status": "unknown",
            })
        
        self.add_sensor_agent("infrared_1")
        
        logger.info(f"[{self.agent_id}] LightHueAgent initialization completed")
    
    def _process_sensor_update(self, sensor_payload: SensorPayload, sensor_id: str):
        """Process sensor data updates from managed sensors."""
        if sensor_payload.sensor_type == "infrared":
            # NOTE(YH): this is a hack to avoid race condition
            with self.state_lock:
                self.sensor_data[sensor_id] = {
                "sensor_type": sensor_payload.sensor_type,
                "value": sensor_payload.value,
                "unit": sensor_payload.unit,
                "metadata": sensor_payload.metadata,
            }
                
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
                assert isinstance(old_sensor_data, dict), f"[YUHENG]meta is {old_sensor_data}, sensor_payload metadata is {sensor_payload.metadata}"
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


    def __turn_on_light(self):
        # Replace with your bridge IP and API username
        # NOTE(YH): hardcode for now
        BRIDGE_IP = "143.248.56.213:10090"
        USERNAME = "P2laHGvjzthn7Ip5-fAAIbVB9ulu9OlHWk8L7Yex"
        BASE_URL = f"http://{BRIDGE_IP}/api/{USERNAME}"
        idx = self.agent_id.split("_")[-1]
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
    
    def turn_off_light(self):
        # Replace with your bridge IP and API username
        # NOTE(YH): hardcode for now
        BRIDGE_IP = "143.248.56.213:10090"
        USERNAME = "P2laHGvjzthn7Ip5-fAAIbVB9ulu9OlHWk8L7Yex"
        BASE_URL = f"http://{BRIDGE_IP}/api/{USERNAME}"
        idx = self.agent_id.split("_")[-1]
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
        """Execute aircon control actions."""
        logger.info(f"[{self.agent_id}] Executing action: {action_payload.actionName}")
        
        try:            
            if action_payload.actionName == "turn_on":
                with self.state_lock:
                    self.local_state["power"] = "on"
                    new_state = self.local_state.copy()
                    result = self.__turn_on_light()
                # success = True
                # message = "Aircon turned on successfully"
                # logger.info(f"[{self.agent_id}] Aircon turned ON")
                # Trigger state publication since local_state changed
                self._trigger_state_publication()
                
            elif action_payload.actionName == "turn_off":
                with self.state_lock:
                    self.local_state["power"] = "off"
                    new_state = self.local_state.copy()
                # success = True
                # message = "Aircon turned off successfully"
                # logger.info(f"[{self.agent_id}] Aircon turned OFF")
                result = self.__turn_off_light()
                # Trigger state publication since local_state changed
                self._trigger_state_publication()
                    
            return result
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error executing action: {e}")
            return {
                "success": False,
                "message": f"Error executing action: {str(e)}"
            }
