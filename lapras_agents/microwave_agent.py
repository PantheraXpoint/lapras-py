import logging
import time
# Phidget Imports
from Phidget22.PhidgetException import PhidgetException, ErrorCode
from Phidget22.Devices.VoltageRatioInput import VoltageRatioInput
from Phidget22.VoltageRatioSensorType import VoltageRatioSensorType
from Phidget22.Unit import Unit
# Lapras Middleware Imports
from lapras_middleware.agent import Agent

logger = logging.getLogger(__name__)

# --- Phidget Configuration for 1105 Light Sensor ---
LIGHT_SENSOR_SERIAL_NUMBER = 455869
LIGHT_SENSOR_CHANNEL = 2
LIGHT_SENSOR_DATA_INTERVAL_MS = 500
# ---

class MicrowaveAgent(Agent):
    def __init__(self, agent_id: str = "microwave_1", mqtt_broker: str = "localhost", mqtt_port: int = 1883):
        self.light_sensor = None
        self._phidget_initialized_successfully = False
        self._last_light_log_time = time.time()
        self._last_init_fail_warn_time = 0 
        self._last_attach_fail_warn_time = 0

        super().__init__(agent_id, mqtt_broker, mqtt_port)
        logger.info(f"[{self.agent_id}] super().__init__ completed.")
        
        with self.state_lock:
            self.local_state.update({
                "microwave/state": "idle",  # <<< KEY MATCHES RULE'S SENSOR PATH
                "environment/light_level": 0.0,
                "environment/light_level_unit": "Unknown"
                # You might also want a specific microwave light sensor reading if needed
                # "microwave/internal_light_reading": 0.0 
            })
        
        try:
            self.initialize_light_sensor()
            if self._phidget_initialized_successfully: # Flag set by attach handler
                logger.info(f"[{self.agent_id}] Phidget 1105 Light Sensor initialization successful.")
            else:
                logger.error(f"[{self.agent_id}] Phidget 1105 Light Sensor initialization FAILED.")
        except Exception as e: 
            logger.error(f"[{self.agent_id}] CRITICAL Exception during Phidget init: {e}")
        
        logger.info(f"[{self.agent_id}] MicrowaveAgent __init__ completed. Phidget init flag: {self._phidget_initialized_successfully}")

    # ... (initialize_light_sensor and Phidget handlers remain the same as previous good version) ...
    def _on_light_sensor_attach(self, ph):
        logger.info(f"[{self.agent_id}_LIGHT_ATTACH] Light Sensor ATTACHED! SN: {ph.getDeviceSerialNumber()}, Ch: {ph.getChannel()}")
        try:
            ph.setSensorType(VoltageRatioSensorType.SENSOR_TYPE_1105)
            ph.setDataInterval(LIGHT_SENSOR_DATA_INTERVAL_MS)
            self._phidget_initialized_successfully = True
            logger.info(f"[{self.agent_id}_LIGHT_ATTACH] Light sensor configured. DataInterval: {ph.getDataInterval()}ms")
        except PhidgetException as e:
            logger.error(f"[{self.agent_id}_LIGHT_ATTACH] Error in attach config: {e.details}")
            self._phidget_initialized_successfully = False
        except Exception as ex:
            logger.error(f"[{self.agent_id}_LIGHT_ATTACH] Generic error in attach config: {str(ex)}")
            self._phidget_initialized_successfully = False


    def _on_light_sensor_detach(self, ph):
        logger.warning(f"[{self.agent_id}_LIGHT_DETACH] Light Sensor DETACHED.")
        self._phidget_initialized_successfully = False

    def _on_light_sensor_error(self, ph, code, description):
        logger.error(f"[{self.agent_id}_LIGHT_ERROR] Phidget ERROR. Code: {code} - {description}")
        if code == ErrorCode.EPHIDGET_NOTATTACHED:
            self._phidget_initialized_successfully = False

    def initialize_light_sensor(self):
        logger.info(f"[{self.agent_id}_LIGHT_INIT] Attempting init for SN: {LIGHT_SENSOR_SERIAL_NUMBER}, Ch: {LIGHT_SENSOR_CHANNEL}")
        try:
            self.light_sensor = VoltageRatioInput()
            self.light_sensor.setOnAttachHandler(self._on_light_sensor_attach)
            self.light_sensor.setOnDetachHandler(self._on_light_sensor_detach)
            self.light_sensor.setOnErrorHandler(self._on_light_sensor_error)
            self.light_sensor.setDeviceSerialNumber(LIGHT_SENSOR_SERIAL_NUMBER)
            self.light_sensor.setChannel(LIGHT_SENSOR_CHANNEL)
            self.light_sensor.setIsHubPortDevice(False)
            self.light_sensor.setSensorType(VoltageRatioSensorType.SENSOR_TYPE_1105)
            self.light_sensor.openWaitForAttachment(5000)
            if not self.light_sensor.getAttached():
                logger.error(f"[{self.agent_id}_LIGHT_INIT] Failed to attach after openWaitForAttachment.")
                self.light_sensor.close() # Clean up
                self.light_sensor = None
                raise PhidgetException(ErrorCode.EPHIDGET_TIMEOUT, "Light sensor attach timeout.")
            logger.info(f"[{self.agent_id}_LIGHT_INIT] Light sensor openWaitForAttachment successful.")
        except PhidgetException as e:
            logger.error(f"[{self.agent_id}_LIGHT_INIT] PhidgetException: {e.details}")
            if self.light_sensor: 
                try: 
                    self.light_sensor.close(); 
                except: 
                    pass
            self.light_sensor = None
            raise
        except Exception as ex:
            logger.error(f"[{self.agent_id}_LIGHT_INIT] Generic Exception: {str(ex)}")
            if self.light_sensor: 
                try: 
                    self.light_sensor.close(); 
                except: 
                    pass
            self.light_sensor = None
            raise


    def perception(self) -> None:
        current_time = time.time()
        light_val = self.local_state.get("environment/light_level", 0.0) # Default to last known
        light_unit = self.local_state.get("environment/light_level_unit", "Unknown")

        if self._phidget_initialized_successfully and self.light_sensor and self.light_sensor.getAttached():
            try:
                raw_value = self.light_sensor.getSensorValue()
                sensor_unit_info = self.light_sensor.getSensorUnit()
                if sensor_unit_info and sensor_unit_info.unit == Unit.PHIDUNIT_LUX:
                    light_val = round(raw_value, 2)
                    light_unit = "Lux"
                elif sensor_unit_info and sensor_unit_info.unit == Unit.PHIDUNIT_NONE:
                    brightness_0_1000 = raw_value * 1000
                    light_val = round(brightness_0_1000, 1)
                    light_unit = "Brightness (0-1000)"
                else: # Fallback
                    light_val = round(raw_value, 4)
                    light_unit = sensor_unit_info.name if sensor_unit_info and sensor_unit_info.name else "Raw"
            except PhidgetException as e:
                if e.code != ErrorCode.EPHIDGET_UNKNOWNVAL: # Don't spam for unknownval
                    logger.error(f"[{self.agent_id}_PERCEPTION] PhidgetException reading Light: {e.details}")
                    self._phidget_initialized_successfully = False # Problem with sensor
            except Exception as e:
                logger.error(f"[{self.agent_id}_PERCEPTION] Generic error reading Light: {str(e)}")
                self._phidget_initialized_successfully = False
        # else: sensor not ready, light_val/light_unit keep previous/default

        # Microwave status logic (example - this would be updated by commands)
        current_microwave_state = self.local_state.get("microwave/state", "idle")
        # If microwave was busy, check if its cooking time ended
        if current_microwave_state == "busy":
            if hasattr(self, '_microwave_cook_end_time') and current_time >= self._microwave_cook_end_time:
                logger.info(f"[{self.agent_id}_PERCEPTION] Microwave finished cooking (simulated).")
                current_microwave_state = "ready" # Or "idle"
                del self._microwave_cook_end_time

        with self.state_lock:
            self.local_state["environment/light_level"] = light_val
            self.local_state["environment/light_level_unit"] = light_unit
            self.local_state["microwave/state"] = current_microwave_state # <<< UPDATE KEY HERE

        if current_time - self._last_light_log_time > 5:
            logger.info(f"[{self.agent_id}_PERCEPTION] Light: {light_val} {light_unit}, Microwave state: {current_microwave_state}")
            self._last_light_log_time = current_time

    def _on_message(self, client, userdata, msg):
        # super()._on_message(client, userdata, msg) # If base class handles context_dist

        try:
            topic = msg.topic
            payload_data = json.loads(msg.payload.decode())
            logger.info(f"[{self.agent_id}_MQTT] Received on topic '{topic}': {payload_data}")

            # Handle ACTION_TAKEN if it comes via a specific MQTT topic
            # or if your rule executor publishes actions to a topic this agent subscribes to.
            # Example: Assuming actions are published to "lapras/action/microwave_1"
            if topic == f"lapras/action/{self.agent_id}": # Or whatever your action topic is
                action_details = payload_data # Assuming payload_data is the action itself
                if action_details.get("device") == "microwave":
                    command = action_details.get("command")
                    parameter = action_details.get("parameter")
                    
                    if command == "start":
                        logger.info(f"[{self.agent_id}_MQTT] Action received: Start microwave, duration: {parameter}")
                        self.handle_microwave_start_command(int(parameter))
                    # Add other commands like "stop", "set_power" if needed
            # Also handle direct state updates from context_dist if your Agent base class does that
            elif topic == "context_dist":
                if payload_data.get("agent_id") == self.agent_id and "state" in payload_data:
                     with self.state_lock:
                        self.local_state.update(payload_data["state"])
                        logger.info(f"[{self.agent_id}_MQTT] Updated local state from context_dist: {payload_data['state']}")


        except json.JSONDecodeError:
            logger.error(f"[{self.agent_id}_MQTT] Non-JSON message on {msg.topic}: {msg.payload}")
        except Exception as e:
            logger.error(f"[{self.agent_id}_MQTT] Error processing MQTT message: {e}")

    def handle_microwave_start_command(self, duration_seconds: int):
        logger.info(f"[{self.agent_id}] Command: Start microwave for {duration_seconds} seconds.")
        with self.state_lock:
            self.local_state["microwave/state"] = "busy" # <<< UPDATE KEY HERE
        self._microwave_cook_end_time = time.time() + duration_seconds
        # Optionally publish an event that microwave has started
        # self.mqtt_client.publish(f"event/{self.agent_id}/status", json.dumps({"status": "busy", "duration": duration_seconds}))


    def stop(self) -> None:
        logger.info(f"[{self.agent_id}] Stopping MicrowaveAgent...")
        if self.light_sensor:
            try:
                if self.light_sensor.getAttached(): self.light_sensor.close()
            except PhidgetException as e: logger.error(f"[{self.agent_id}_STOP] Error closing light sensor: {e.details}")
            self.light_sensor = None
        self._phidget_initialized_successfully = False

        with self.state_lock:
            self.local_state["microwave/state"] = "idle" # <<< UPDATE KEY HERE
        
        super().stop()
        logger.info(f"[{self.agent_id}] MicrowaveAgent stopped.")