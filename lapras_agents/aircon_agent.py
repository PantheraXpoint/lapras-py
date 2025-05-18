import logging
import time
# from Phidget22.Phidget import Phidget # Keep commented for finalize
from Phidget22.PhidgetException import PhidgetException, ErrorCode
from Phidget22.Devices.VoltageRatioInput import VoltageRatioInput
from Phidget22.VoltageRatioSensorType import VoltageRatioSensorType # Keep for consistency, though not strictly used in this minimal init
from Phidget22.Unit import Unit 
from lapras_middleware.agent import Agent

logger = logging.getLogger(__name__)

class AirconAgent(Agent):
    def __init__(self, agent_id: str = "aircon", mqtt_broker: str = "localhost", mqtt_port: int = 1883):
        self.ir_sensor = None
        self._phidget_initialized_successfully = False
        # Initialize other rate-limiting time trackers if used in perception
        self._last_init_fail_warn_time = 0
        self._last_attach_fail_warn_time = 0
        self._last_dist_log_time = 0

        super().__init__(agent_id, mqtt_broker, mqtt_port)
        logger.info(f"[AIRCON] super().__init__ completed for agent '{agent_id}'.")
        
        with self.state_lock:
            self.local_state.update({"distance": 0.0, "power": "off"})
        
        try:
            self.initialize_ir_sensor_minimal() # Call the minimal initializer
            if self.ir_sensor and self.ir_sensor.getAttached():
                self._phidget_initialized_successfully = True
                logger.info("[AIRCON] Minimal Phidget IR sensor initialization was SUCCESSFUL in __init__.")
            else:
                logger.error("[AIRCON] Minimal Phidget IR sensor initialization FAILED in __init__ (sensor not attached or None).")
        except Exception as e: 
            logger.error(f"[AIRCON] CRITICAL Exception during minimal Phidget init call in __init__: {type(e).__name__} - {e}")
        
        logger.info(f"[AIRCON] AirconAgent __init__ completed. Phidget initialized flag: {self._phidget_initialized_successfully}")

    def initialize_ir_sensor_minimal(self):
        """Extremely simplified Phidget initialization for debugging."""
        logger.info("[AIRCON_INIT_MINIMAL] Attempting MINIMAL IR sensor initialization...")
        self.ir_sensor = None # Ensure it starts as None

        # --- Device Parameters ---
        DEVICE_SERIAL_NUMBER = 455252  # YOUR CONFIRMED SERIAL NUMBER
        TARGET_CHANNEL = 2
        OPEN_TIMEOUT_MS = 5000
        # --- End Parameters ---

        try:
            logger.info(f"[AIRCON_INIT_MINIMAL] 1. Creating VoltageRatioInput object.")
            ch = VoltageRatioInput() # Use a local variable for clarity in this test

            logger.info(f"[AIRCON_INIT_MINIMAL] 2. Setting DeviceSerialNumber to {DEVICE_SERIAL_NUMBER}.")
            ch.setDeviceSerialNumber(DEVICE_SERIAL_NUMBER)

            logger.info(f"[AIRCON_INIT_MINIMAL] 3. Setting Channel to {TARGET_CHANNEL}.")
            ch.setChannel(TARGET_CHANNEL)
            
            logger.info(f"[AIRCON_INIT_MINIMAL] 4. Setting setIsHubPortDevice(False).")
            ch.setIsHubPortDevice(False)

            # Not setting handlers or SensorType or DataInterval *before* open for this minimal test.
            # openWaitForAttachment should still find a generic VoltageRatioInput if SN and Channel match.

            logger.info(f"[AIRCON_INIT_MINIMAL] 5. Calling openWaitForAttachment({OPEN_TIMEOUT_MS}ms)...")
            ch.openWaitForAttachment(OPEN_TIMEOUT_MS) # This is the blocking call

            # Check attachment status *immediately* after openWaitForAttachment returns
            if ch.getAttached():
                logger.info(f"[AIRCON_INIT_MINIMAL] SUCCESS! Phidget ATTACHED. SN: {ch.getDeviceSerialNumber()}, Ch: {ch.getChannel()}")
                # Now that it's attached, we can try to set SensorType and DataInterval
                try:
                    logger.info("[AIRCON_INIT_MINIMAL] Setting SensorType to VOLTAGERATIO post-attach.")
                    ch.setSensorType(VoltageRatioSensorType.SENSOR_TYPE_VOLTAGERATIO)
                    logger.info("[AIRCON_INIT_MINIMAL] Setting DataInterval to 200ms post-attach.")
                    ch.setDataInterval(200)
                    logger.info("[AIRCON_INIT_MINIMAL] Post-attach configuration complete.")
                    self.ir_sensor = ch # Assign to the instance variable ONLY upon full success
                except PhidgetException as pe_post_attach:
                    logger.error(f"[AIRCON_INIT_MINIMAL] PhidgetException during post-attach config: {pe_post_attach.code} - {pe_post_attach.details}")
                    ch.close() # Clean up the channel that attached but failed post-config
                    self.ir_sensor = None
                    raise # Re-raise to signal overall init failure
            else:
                logger.error("[AIRCON_INIT_MINIMAL] FAILED. openWaitForAttachment completed, but Phidget is NOT attached.")
                # No need to call ch.close() if it never attached
                self.ir_sensor = None
                raise PhidgetException(ErrorCode.EPHIDGET_TIMEOUT, "Minimal Initialize IR: openWaitForAttachment returned but not attached.")

        except PhidgetException as e: 
            logger.error(f"[AIRCON_INIT_MINIMAL] PhidgetException in minimal_initialize_ir_sensor: {e.code} ({hex(e.code)}) - {e.details}")
            # If 'ch' object exists and might be open or in a strange state, try to close it
            if 'ch' in locals() and ch is not None:
                try: ch.close()
                except: pass
            self.ir_sensor = None # Ensure instance variable is None
            raise # Re-raise to propagate the error to __init__
        except Exception as ex: 
            logger.error(f"[AIRCON_INIT_MINIMAL] Generic Exception in minimal_initialize_ir_sensor: {str(ex)}")
            if 'ch' in locals() and ch is not None:
                try: ch.close()
                except: pass
            self.ir_sensor = None
            raise

    # Keep your existing _on_ir_attach, _on_ir_detach, _on_ir_error methods
    # They won't be used by initialize_ir_sensor_minimal unless you re-add setOnAttachHandler etc.
    # but they are good to have for a more complete implementation later.
    def _on_ir_attach(self, ph):
        # ... (your previous robust _on_ir_attach handler)
        logger.info(f"[AIRCON_ATTACH_HANDLER_UNUSED_IN_MINIMAL] IR Sensor ATTACHED! SN: {ph.getDeviceSerialNumber()}, Ch: {ph.getChannel()}")
        self._phidget_initialized_successfully = True # Set flag here if using this handler

    def _on_ir_detach(self, ph):
        # ... (your previous _on_ir_detach handler)
        logger.warning(f"[AIRCON_DETACH_HANDLER_UNUSED_IN_MINIMAL] IR Sensor DETACHED. SN: {ph.getDeviceSerialNumber()}, Ch: {ph.getChannel()}")
        self._phidget_initialized_successfully = False

    def _on_ir_error(self, ph, code, description):
        # ... (your previous _on_ir_error handler)
        sn_str = str(ph.getDeviceSerialNumber()) if ph and hasattr(ph, 'getDeviceSerialNumber') else 'N/A'
        ch_str = str(ph.getChannel()) if ph and hasattr(ph, 'getChannel') else 'N/A'
        logger.error(f"[AIRCON_ERROR_HANDLER_UNUSED_IN_MINIMAL] Phidget ERROR. SN: {sn_str}, Ch: {ch_str}. Code: {code} ({hex(code)}) - {description}")
        if code == ErrorCode.EPHIDGET_NOTATTACHED:
            self._phidget_initialized_successfully = False

    # Keep your existing perception and stop methods
    # They will use self.ir_sensor and self._phidget_initialized_successfully
    def perception(self) -> None:
        # ... (your previous perception method) ...
        if not self._phidget_initialized_successfully: 
            if time.time() - getattr(self, '_last_init_fail_warn_time', 0) > 5: # Rate limit warning
                logger.warning("[AIRCON_PERCEPTION] IR sensor not successfully initialized or became detached; perception skipped.")
                self._last_init_fail_warn_time = time.time()
            return
        if not self.ir_sensor or not self.ir_sensor.getAttached(): # Check if sensor object exists and is attached
            if time.time() - getattr(self, '_last_attach_fail_warn_time', 0) > 5: # Rate limit warning
                logger.warning("[AIRCON_PERCEPTION] IR sensor object missing or not attached in perception check; perception skipped.")
                self._last_attach_fail_warn_time = time.time()
            self._phidget_initialized_successfully = False # Update status
            return
        try:
            voltage_ratio = self.ir_sensor.getVoltageRatio()
            sensor_value_for_formula = voltage_ratio * 1000
            
            # --- IMPORTANT: Select Sensor Configuration ---
            # Choose ONE of the configurations below based on your sensor model.
            # Currently configured for Sharp 2Y0A02 (Phidgets 3522 / 20-150cm)

            # Configuration for: Sharp 2Y0A02 (Phidgets 3522 / 20-150cm sensor)
            SENSOR_MODEL_NAME = "Sharp 2Y0A02 (20-150cm)"
            SENSOR_MIN_CM = 20.0
            SENSOR_MAX_CM = 150.0
            FORMULA_VALID_SV_MIN = 80.0  # Valid "SensorValue" range for this formula (from Phidgets)
            FORMULA_VALID_SV_MAX = 490.0  # Valid "SensorValue" range for this formula (from Phidgets)
            K_DISTANCE = 9462.0          # Formula constant K (from Phidgets)
            SV_OFFSET = 16.92            # Formula constant Offset (from Phidgets)

            # # Configuration for: Sharp 2Y0A21 (Phidgets 3521 / 10-80cm sensor)
            # SENSOR_MODEL_NAME = "Sharp 2Y0A21 (10-80cm)"
            # SENSOR_MIN_CM = 10.0
            # SENSOR_MAX_CM = 80.0
            # FORMULA_VALID_SV_MIN = 80.0
            # FORMULA_VALID_SV_MAX = 500.0
            # K_DISTANCE = 4800.0
            # SV_OFFSET = 20.0

            # # Configuration for: Sharp 2D120X (Phidgets 3520 / 4-30cm sensor)
            # SENSOR_MODEL_NAME = "Sharp 2D120X (4-30cm)"
            # SENSOR_MIN_CM = 4.0
            # SENSOR_MAX_CM = 30.0
            # FORMULA_VALID_SV_MIN = 80.0
            # FORMULA_VALID_SV_MAX = 530.0 # Note: Phidgets image says 80-530, be careful with text interpretation
            # K_DISTANCE = 2076.0
            # SV_OFFSET = 11.0
            # --- End Sensor Configuration ---
            
            calculated_cm = SENSOR_MAX_CM # Default to max distance
            
                
            if sensor_value_for_formula >= FORMULA_VALID_SV_MIN and sensor_value_for_formula <= FORMULA_VALID_SV_MAX:
                # The formula is Distance(cm) = K / (SensorValue - Offset)
                # Ensure denominator is positive (it should be, as FORMULA_VALID_SV_MIN > SV_OFFSET for these sensors)
                denominator = sensor_value_for_formula - SV_OFFSET
                if denominator > 0.01: # Avoid division by zero or extremely small positive numbers
                    distance_from_formula = K_DISTANCE / denominator
                    # Clamp the result of the formula to the sensor's actual min/max physical range
                    calculated_cm = max(SENSOR_MIN_CM, min(SENSOR_MAX_CM, distance_from_formula))
                else:
                    # This case implies SensorValue is very close to Offset, meaning very near.
                    calculated_cm = SENSOR_MIN_CM
            elif sensor_value_for_formula < FORMULA_VALID_SV_MIN:
                # SensorValue is too low (voltage too low), implies object is far or beyond max range
                calculated_cm = SENSOR_MAX_CM
            elif sensor_value_for_formula > FORMULA_VALID_SV_MAX:
                # SensorValue is too high (voltage too high), implies object is too close, below min range or error
                calculated_cm = SENSOR_MIN_CM
                
            # --- Proximity Classification ---
            # Define your threshold for "near" vs "far" in centimeters
            # Example: if distance is less than 100cm (1 meter), it's "near"
            PROXIMITY_THRESHOLD_CM = 100.0
            proximity_status = "unknown" # Default status

            if calculated_cm < PROXIMITY_THRESHOLD_CM:
                proximity_status = "near"
            else: # Covers calculated_cm >= PROXIMITY_THRESHOLD_CM and out-of-range defaults
                proximity_status = "far"
            # --- End Proximity Classification ---
                
                
            with self.state_lock:
                self.local_state["distance"] = round(calculated_cm, 2)
                self.local_state["proximity_status"] = proximity_status # New state variable
                # Ensure power state is initialized if not present
                if "power" not in self.local_state:
                    self.local_state["power"] = "off" # Default
                    
            if time.time() - getattr(self, '_last_dist_log_time', 0) > 2: 
                logger.info(
                    f"[AIRCON_PERCEPTION] Sensor: {SENSOR_MODEL_NAME}, "
                    f"Distance: {self.local_state.get('distance', 'N/A'):.2f}cm, "
                    f"Proximity: {self.local_state.get('proximity_status', 'N/A')}, "
                    f"Power: {self.local_state.get('power', 'N/A')}, "
                    f"(Raw Ratio: {voltage_ratio:.4f}, SensorValueForFormula: {sensor_value_for_formula:.1f})"
                )
                self._last_dist_log_time = time.time()
        except PhidgetException as e: # Make sure PhidgetException is imported or defined
            if e.code == ErrorCode.EPHIDGET_UNKNOWNVAL: # Make sure ErrorCode is imported or defined
                if current_time - getattr(self, '_last_unknown_val_warn_time', 0) > 5:
                    logger.warning(f"[AIRCON_PERCEPTION] IR sensor value unknown (EPHIDGET_UNKNOWNVAL).")
                    self._last_unknown_val_warn_time = current_time
            elif e.code == ErrorCode.EPHIDGET_NOTATTACHED:
                logger.error(f"[AIRCON_PERCEPTION] PhidgetException: Sensor not attached during read. {e.details}")
                self._phidget_initialized_successfully = False
            else:
                logger.error(f"[AIRCON_PERCEPTION] PhidgetException reading IR sensor: {e.code} ({hex(e.code)}) - {e.details}")
                self._phidget_initialized_successfully = False
        except Exception as e:
            logger.error(f"[AIRCON_PERCEPTION] Generic error in perception: {type(e).__name__} - {str(e)}")
            self._phidget_initialized_successfully = False


    def stop(self) -> None:
        # ... (your previous stop method with Phidget.finalize(0) commented out) ...
        logger.info("[AIRCON_STOP] Stopping air conditioner agent...")
        with self.state_lock:
            self.local_state["power"] = "off" 
        if self.ir_sensor:
            is_attached_before_close = False
            try:
                is_attached_before_close = self.ir_sensor.getAttached()
            except: pass 
            logger.info(f"[AIRCON_STOP] Attempting to close IR sensor. Was attached: {is_attached_before_close}")
            try:
                self.ir_sensor.close() 
                logger.info("[AIRCON_STOP] IR sensor close() called.")
            except PhidgetException as e:
                logger.error(f"[AIRCON_STOP] Error closing IR sensor: {e.code} - {e.details}")
            self.ir_sensor = None 
        self._phidget_initialized_successfully = False
        super().stop() 
        logger.info("[AIRCON_STOP] AirconAgent agent stop sequence complete.")