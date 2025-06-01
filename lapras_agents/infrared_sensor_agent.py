import logging
import time
from typing import Optional, Any, Dict
from Phidget22.PhidgetException import PhidgetException, ErrorCode
from Phidget22.Devices.VoltageRatioInput import VoltageRatioInput
from Phidget22.VoltageRatioSensorType import VoltageRatioSensorType

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lapras_middleware.sensor_agent import SensorAgent

logger = logging.getLogger(__name__)

class InfraredSensorAgent(SensorAgent):
    """Infrared distance sensor agent using Phidget sensor."""
    
    def __init__(self, sensor_id: str = "infrared_1", virtual_agent_id: str = "aircon", 
                 mqtt_broker: str = "143.248.57.73", mqtt_port: int = 1883):
        # Phidget sensor
        self.ir_sensor: Optional[VoltageRatioInput] = None
        self._phidget_initialized_successfully = False
        
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
        self.DEVICE_SERIAL_NUMBER = 455252
        self.TARGET_CHANNEL = 2
        self.OPEN_TIMEOUT_MS = 5000
        
        # Rate limiting
        self._last_init_fail_warn_time = 0
        self._last_attach_fail_warn_time = 0
        self._last_unknown_val_warn_time = 0
        
        # Initialize the base SensorAgent class AFTER setting attributes
        super().__init__(sensor_id, "infrared", virtual_agent_id, mqtt_broker, mqtt_port)
        
        # Initialize sensor hardware after everything is set up
        self.start_sensor()
        
        logger.info(f"[{self.agent_id}] InfraredSensorAgent initialized")
    
    def initialize_sensor(self):
        """Initialize the Phidget infrared sensor."""
        logger.info(f"[{self.agent_id}] Initializing infrared sensor...")
        self.ir_sensor = None
        
        try:
            logger.info(f"[{self.agent_id}] Creating VoltageRatioInput object")
            ch = VoltageRatioInput()
            
            logger.info(f"[{self.agent_id}] Setting DeviceSerialNumber to {self.DEVICE_SERIAL_NUMBER}")
            ch.setDeviceSerialNumber(self.DEVICE_SERIAL_NUMBER)
            
            logger.info(f"[{self.agent_id}] Setting Channel to {self.TARGET_CHANNEL}")
            ch.setChannel(self.TARGET_CHANNEL)
            
            logger.info(f"[{self.agent_id}] Setting setIsHubPortDevice(False)")
            ch.setIsHubPortDevice(False)
            
            logger.info(f"[{self.agent_id}] Calling openWaitForAttachment({self.OPEN_TIMEOUT_MS}ms)...")
            ch.openWaitForAttachment(self.OPEN_TIMEOUT_MS)
            
            # Check attachment status
            if ch.getAttached():
                logger.info(f"[{self.agent_id}] SUCCESS! Phidget ATTACHED. SN: {ch.getDeviceSerialNumber()}, Ch: {ch.getChannel()}")
                
                # Configure sensor post-attach
                try:
                    logger.info(f"[{self.agent_id}] Setting SensorType to VOLTAGERATIO post-attach")
                    ch.setSensorType(VoltageRatioSensorType.SENSOR_TYPE_VOLTAGERATIO)
                    logger.info(f"[{self.agent_id}] Setting DataInterval to 200ms post-attach")
                    ch.setDataInterval(200)
                    logger.info(f"[{self.agent_id}] Post-attach configuration complete")
                    
                    self.ir_sensor = ch
                    self._phidget_initialized_successfully = True
                    logger.info(f"[{self.agent_id}] Infrared sensor initialization successful")
                    
                except PhidgetException as pe_post_attach:
                    logger.error(f"[{self.agent_id}] PhidgetException during post-attach config: {pe_post_attach.code} - {pe_post_attach.details}")
                    ch.close()
                    self.ir_sensor = None
                    raise
            else:
                logger.error(f"[{self.agent_id}] FAILED. openWaitForAttachment completed, but Phidget is NOT attached")
                self.ir_sensor = None
                raise PhidgetException(ErrorCode.EPHIDGET_TIMEOUT, "openWaitForAttachment returned but not attached")
                
        except PhidgetException as e:
            logger.error(f"[{self.agent_id}] PhidgetException in initialize_sensor: {e.code} ({hex(e.code)}) - {e.details}")
            if 'ch' in locals() and ch is not None:
                try:
                    ch.close()
                except:
                    pass
            self.ir_sensor = None
            self._phidget_initialized_successfully = False
            raise
        except Exception as ex:
            logger.error(f"[{self.agent_id}] Generic Exception in initialize_sensor: {str(ex)}")
            if 'ch' in locals() and ch is not None:
                try:
                    ch.close()
                except:
                    pass
            self.ir_sensor = None
            self._phidget_initialized_successfully = False
            raise
    
    def cleanup_sensor(self):
        """Clean up the Phidget infrared sensor."""
        logger.info(f"[{self.agent_id}] Cleaning up infrared sensor...")
        
        if self.ir_sensor:
            is_attached_before_close = False
            try:
                is_attached_before_close = self.ir_sensor.getAttached()
            except:
                pass
            
            logger.info(f"[{self.agent_id}] Attempting to close IR sensor. Was attached: {is_attached_before_close}")
            try:
                self.ir_sensor.close()
                logger.info(f"[{self.agent_id}] IR sensor close() called")
            except PhidgetException as e:
                logger.error(f"[{self.agent_id}] Error closing IR sensor: {e.code} - {e.details}")
            
            self.ir_sensor = None
        
        self._phidget_initialized_successfully = False
        logger.info(f"[{self.agent_id}] Infrared sensor cleanup complete")
    
    def read_sensor(self) -> tuple[Any, Optional[str], Optional[Dict[str, Any]]]:
        """Read the infrared sensor value and calculate distance."""
        if not self._phidget_initialized_successfully:
            current_time = time.time()
            if current_time - self._last_init_fail_warn_time > 5:
                logger.warning(f"[{self.agent_id}] IR sensor not successfully initialized; skipping read")
                self._last_init_fail_warn_time = current_time
            return None, None, None
        
        if not self.ir_sensor or not self.ir_sensor.getAttached():
            current_time = time.time()
            if current_time - self._last_attach_fail_warn_time > 5:
                logger.warning(f"[{self.agent_id}] IR sensor object missing or not attached; skipping read")
                self._last_attach_fail_warn_time = current_time
            self._phidget_initialized_successfully = False
            return None, None, None
        
        try:
            voltage_ratio = self.ir_sensor.getVoltageRatio()
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
                "threshold_cm": self.PROXIMITY_THRESHOLD_CM
            }
            
            return round(calculated_cm, 2), "cm", metadata
            
        except PhidgetException as e:
            current_time = time.time()
            if e.code == ErrorCode.EPHIDGET_UNKNOWNVAL:
                if current_time - self._last_unknown_val_warn_time > 5:
                    logger.warning(f"[{self.agent_id}] IR sensor value unknown (EPHIDGET_UNKNOWNVAL)")
                    self._last_unknown_val_warn_time = current_time
            elif e.code == ErrorCode.EPHIDGET_NOTATTACHED:
                logger.error(f"[{self.agent_id}] PhidgetException: Sensor not attached during read. {e.details}")
                self._phidget_initialized_successfully = False
            else:
                logger.error(f"[{self.agent_id}] PhidgetException reading IR sensor: {e.code} ({hex(e.code)}) - {e.details}")
                self._phidget_initialized_successfully = False
            return None, None, None
        except Exception as e:
            logger.error(f"[{self.agent_id}] Generic error reading sensor: {type(e).__name__} - {str(e)}")
            self._phidget_initialized_successfully = False
            return None, None, None 