import logging
import time
from typing import Optional, Any, Dict, List
from Phidget22.PhidgetException import PhidgetException, ErrorCode
from Phidget22.Devices.VoltageRatioInput import VoltageRatioInput
from Phidget22.VoltageRatioSensorType import VoltageRatioSensorType

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lapras_middleware.sensor_agent import SensorAgent
from lapras_middleware.event import EventFactory, MQTTMessage, TopicManager

logger = logging.getLogger(__name__)

class InfraredSensorAgent(SensorAgent):
    """Infrared distance sensor agent using Phidget sensor with 3 channels."""

    def __init__(self, sensor_id: str = "infrared", virtual_agent_id: str = "aircon", channel: int = 1,
                 mqtt_broker: str = "143.248.57.73", mqtt_port: int = 1883):
        # Phidget sensors for 3 channels
        self.ir_sensors: Dict[int, Optional[VoltageRatioInput]] = {}
        self.sensor_initialized: Dict[int, bool] = {}
        self.channels = [channel, channel + 1, channel + 2]
        
        # Create sensor IDs for each channel (infrared_1, infrared_2, infrared_3)
        self.sensor_ids = [f"{sensor_id}_{i+1}" for i in range(len(self.channels))]
        
        # Create a mapping of channels to sensor IDs
        self.channel_to_sensor_id = dict(zip(self.channels, self.sensor_ids))
        
        # Sensor configuration (Sharp 2Y0A02 - 20-150cm)
        self.SENSOR_MODEL_NAME = "Sharp 2Y0A02 (20-150cm)"
        self.SENSOR_MIN_CM = 20.0
        self.SENSOR_MAX_CM = 150.0
        self.FORMULA_VALID_SV_MIN = 80.0
        self.FORMULA_VALID_SV_MAX = 490.0
        self.K_DISTANCE = 9462.0
        self.SV_OFFSET = 16.92
        self.PROXIMITY_THRESHOLD_CM = 100.0

        # Device parameters
        self.DEVICE_SERIAL_NUMBER = 455869  # run this command to see the serial number "phidget22admin -d"
        self.TARGET_CHANNEL = channel
        self.OPEN_TIMEOUT_MS = 5000

        # Rate limiting for warnings per channel
        self._last_warn_times: Dict[int, Dict[str, float]] = {}
        for ch in self.channels:
            self.sensor_initialized[ch] = False
            self._last_warn_times[ch] = {
                'init_fail': 0,
                'attach_fail': 0,
                'unknown_val': 0
            }

        # Initialize the base SensorAgent class with the first sensor ID
        # (This is mainly for compatibility with the parent class)
        super().__init__(self.sensor_ids[0], "infrared", virtual_agent_id, mqtt_broker, mqtt_port)

        # Initialize sensor hardware after everything is set up
        self.start_sensor()

        logger.info(f"[{self.agent_id}] InfraredSensorAgent initialized for channels {self.channels} with sensor IDs {self.sensor_ids}")

    def _read_and_publish(self):
        """Override parent method to publish each channel to its own topic."""
        try:
            self.reading_count += 1
            # Read all channels and publish each one separately
            for channel in self.channels:
                value, unit, metadata = self.read_sensor_channel(channel)
                
                if value is not None:
                    sensor_id = self.channel_to_sensor_id[channel]
                    
                    # Create readSensor event for this specific channel
                    event = EventFactory.create_sensor_event(
                        sensor_id=sensor_id,
                        virtual_agent_id="*",  # Broadcast to all interested virtual agents
                        sensor_type=self.sensor_type,
                        value=value,
                        unit=unit,
                        metadata=metadata
                    )
                    
                    # Publish to MQTT using the broadcast topic pattern for this specific sensor ID
                    topic = TopicManager.sensor_broadcast(sensor_id)
                    message = MQTTMessage.serialize(event)
                    self.mqtt_client.publish(topic, message, qos=1)
                    logger.info(f"[{self.agent_id}] Published {sensor_id} reading #{self.reading_count}: {value} {unit} to topic: {topic}")
                    
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error reading/publishing sensor data: {e}")

    # Keep all your existing methods unchanged
    def initialize_sensor(self):
        """Initialize the Phidget infrared sensors for all 3 channels."""
        logger.info(f"[{self.agent_id}] Initializing infrared sensors for channels {self.channels}...")

        # Clear any existing sensors
        for ch in self.channels:
            self.ir_sensors[ch] = None
            self.sensor_initialized[ch] = False

        try:
            sensors = []
            for i, channel in enumerate(self.channels):
                logger.info(f"[{self.agent_id}] Creating VoltageRatioInput object for channel {channel}")
                sensor = VoltageRatioInput()

                logger.info(f"[{self.agent_id}] Setting DeviceSerialNumber to {self.DEVICE_SERIAL_NUMBER} for channel {channel}")
                sensor.setDeviceSerialNumber(self.DEVICE_SERIAL_NUMBER)

                logger.info(f"[{self.agent_id}] Setting Channel to {channel}")
                sensor.setChannel(channel)

                logger.info(f"[{self.agent_id}] Setting setIsHubPortDevice(False) for channel {channel}")
                sensor.setIsHubPortDevice(False)

                sensors.append((channel, sensor))

            # Open all sensors
            logger.info(f"[{self.agent_id}] Opening all sensors...")
            for channel, sensor in sensors:
                logger.info(f"[{self.agent_id}] Calling openWaitForAttachment({self.OPEN_TIMEOUT_MS}ms) for channel {channel}...")
                sensor.openWaitForAttachment(self.OPEN_TIMEOUT_MS)

            # Check attachment status and configure
            all_attached = True
            for channel, sensor in sensors:
                if sensor.getAttached():
                    logger.info(f"[{self.agent_id}] SUCCESS! Channel {channel} Phidget ATTACHED. SN: {sensor.getDeviceSerialNumber()}")
                    try:
                        logger.info(f"[{self.agent_id}] Setting SensorType to VOLTAGERATIO for channel {channel}")
                        sensor.setSensorType(VoltageRatioSensorType.SENSOR_TYPE_VOLTAGERATIO)
                        logger.info(f"[{self.agent_id}] Setting DataInterval to 200ms for channel {channel}")
                        sensor.setDataInterval(200)

                        self.ir_sensors[channel] = sensor
                        self.sensor_initialized[channel] = True
                        logger.info(f"[{self.agent_id}] Channel {channel} initialization successful")

                    except PhidgetException as pe_post_attach:
                        logger.error(f"[{self.agent_id}] PhidgetException during post-attach config for channel {channel}: {pe_post_attach.code} - {pe_post_attach.details}")
                        sensor.close()
                        all_attached = False
                else:
                    logger.error(f"[{self.agent_id}] FAILED. Channel {channel} openWaitForAttachment completed, but Phidget is NOT attached")
                    sensor.close()
                    all_attached = False

            if all_attached:
                logger.info(f"[{self.agent_id}] All infrared sensors initialization successful")
            else:
                logger.error(f"[{self.agent_id}] Some sensors failed to initialize")
                # Clean up any successfully opened sensors
                for channel, sensor in sensors:
                    try:
                        sensor.close()
                    except:
                        pass
                    self.ir_sensors[channel] = None
                    self.sensor_initialized[channel] = False
                raise PhidgetException(ErrorCode.EPHIDGET_TIMEOUT, "Some sensors failed to attach")

        except PhidgetException as e:
            logger.error(f"[{self.agent_id}] PhidgetException in initialize_sensor: {e.code} ({hex(e.code)}) - {e.details}")
            # Clean up
            for channel in self.channels:
                if channel in self.ir_sensors and self.ir_sensors[channel]:
                    try:
                        self.ir_sensors[channel].close()
                    except:
                        pass
                    self.ir_sensors[channel] = None
                    self.sensor_initialized[channel] = False
            raise
        except Exception as ex:
            logger.error(f"[{self.agent_id}] Generic Exception in initialize_sensor: {str(ex)}")
            # Clean up
            for channel in self.channels:
                if channel in self.ir_sensors and self.ir_sensors[channel]:
                    try:
                        self.ir_sensors[channel].close()
                    except:
                        pass
                    self.ir_sensors[channel] = None
                    self.sensor_initialized[channel] = False
            raise

    def cleanup_sensor(self):
        """Clean up all Phidget infrared sensors."""
        logger.info(f"[{self.agent_id}] Cleaning up infrared sensors...")

        for channel in self.channels:
            if channel in self.ir_sensors and self.ir_sensors[channel]:
                is_attached_before_close = False
                try:
                    is_attached_before_close = self.ir_sensors[channel].getAttached()
                except:
                    pass

                logger.info(f"[{self.agent_id}] Attempting to close channel {channel} sensor. Was attached: {is_attached_before_close}")
                try:
                    self.ir_sensors[channel].close()
                    logger.info(f"[{self.agent_id}] Channel {channel} sensor close() called")
                except PhidgetException as e:
                    logger.error(f"[{self.agent_id}] Error closing channel {channel} sensor: {e.code} - {e.details}")

                self.ir_sensors[channel] = None

            self.sensor_initialized[channel] = False

        logger.info(f"[{self.agent_id}] Infrared sensors cleanup complete")

    def read_sensor_channel(self, channel: int) -> tuple[Any, Optional[str], Optional[Dict[str, Any]]]:
        """Read a specific sensor channel and calculate distance."""
        if not self.sensor_initialized.get(channel, False):
            current_time = time.time()
            if current_time - self._last_warn_times[channel]['init_fail'] > 5:
                logger.warning(f"[{self.agent_id}] Channel {channel} sensor not initialized; skipping read")
                self._last_warn_times[channel]['init_fail'] = current_time
            return None, None, None

        sensor = self.ir_sensors.get(channel)
        if not sensor or not sensor.getAttached():
            current_time = time.time()
            if current_time - self._last_warn_times[channel]['attach_fail'] > 5:
                logger.warning(f"[{self.agent_id}] Channel {channel} sensor not attached; skipping read")
                self._last_warn_times[channel]['attach_fail'] = current_time
            self.sensor_initialized[channel] = False
            return None, None, None

        try:
            voltage_ratio = sensor.getVoltageRatio()
            sensor_value_for_formula = voltage_ratio * 1000

            calculated_cm = self.SENSOR_MAX_CM  # Default to max distance

            if sensor_value_for_formula >= self.FORMULA_VALID_SV_MIN and sensor_value_for_formula <= self.FORMULA_VALID_SV_MAX:
                denominator = sensor_value_for_formula - self.SV_OFFSET
                if denominator > 0.01:
                    distance_from_formula = self.K_DISTANCE / denominator
                    calculated_cm = max(self.SENSOR_MIN_CM, min(self.SENSOR_MAX_CM, distance_from_formula))
                else:
                    calculated_cm = self.SENSOR_MIN_CM
            elif sensor_value_for_formula < self.FORMULA_VALID_SV_MIN:
                calculated_cm = self.SENSOR_MAX_CM
            elif sensor_value_for_formula > self.FORMULA_VALID_SV_MAX:
                calculated_cm = self.SENSOR_MIN_CM

            # Determine proximity status
            proximity_status = "near" if calculated_cm < self.PROXIMITY_THRESHOLD_CM else "far"

            # Prepare metadata
            metadata = {
                "proximity_status": proximity_status,
                "raw_voltage_ratio": voltage_ratio,
                "sensor_value": sensor_value_for_formula,
                "sensor_model": self.SENSOR_MODEL_NAME,
                "threshold_cm": self.PROXIMITY_THRESHOLD_CM,
                "channel": channel
            }

            return round(calculated_cm, 2), "cm", metadata

        except PhidgetException as e:
            current_time = time.time()
            if e.code == ErrorCode.EPHIDGET_UNKNOWNVAL:
                if current_time - self._last_warn_times[channel]['unknown_val'] > 5:
                    logger.warning(f"[{self.agent_id}] Channel {channel} sensor value unknown (EPHIDGET_UNKNOWNVAL)")
                    self._last_warn_times[channel]['unknown_val'] = current_time
            elif e.code == ErrorCode.EPHIDGET_NOTATTACHED:
                logger.error(f"[{self.agent_id}] Channel {channel} PhidgetException: Sensor not attached during read. {e.details}")
                self.sensor_initialized[channel] = False
            else:
                logger.error(f"[{self.agent_id}] Channel {channel} PhidgetException reading sensor: {e.code} ({hex(e.code)}) - {e.details}")
                self.sensor_initialized[channel] = False
            return None, None, None
        except Exception as e:
            logger.error(f"[{self.agent_id}] Channel {channel} generic error reading sensor: {type(e).__name__} - {str(e)}")
            self.sensor_initialized[channel] = False
            return None, None, None

    def read_sensor(self) -> tuple[Any, Optional[str], Optional[Dict[str, Any]]]:
        """Read all infrared sensor channels and return combined data."""
        all_readings = {}
        any_success = False

        for channel in self.channels:
            value, unit, metadata = self.read_sensor_channel(channel)
            if value is not None:
                all_readings[f"channel_{channel}"] = {
                    "value": value,
                    "unit": unit,
                    "metadata": metadata
                }
                any_success = True

        if not any_success:
            return None, None, None

        # Create combined metadata with all channel data
        combined_metadata = {
            "sensor_model": self.SENSOR_MODEL_NAME,
            "threshold_cm": self.PROXIMITY_THRESHOLD_CM,
            "channels": self.channels,
            "readings": all_readings
        }

        # For compatibility, return the first successful reading as the primary value
        # but include all data in metadata
        primary_channel = None
        primary_value = None
        for channel in self.channels:
            if f"channel_{channel}" in all_readings:
                primary_channel = channel
                primary_value = all_readings[f"channel_{channel}"]["value"]
                break

        combined_metadata["primary_channel"] = primary_channel

        return primary_value, "cm", combined_metadata