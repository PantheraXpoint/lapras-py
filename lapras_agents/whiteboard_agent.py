import logging
import time
from typing import Optional
from lapras_middleware.agent import AgentComponent
from lapras_middleware.context import Context, ContextField
from lapras_middleware.event import Event, EventDispatcher

logger = logging.getLogger(__name__)

class WhiteboardAgent(AgentComponent):
    """
    WhiteboardAgent monitors whiteboard usage using IR sensors.
    """
    
    def __init__(self, event_dispatcher: EventDispatcher, agent):
        super().__init__(event_dispatcher, agent)
        
        # Context fields
        self.whiteboard_used = False
        self.current = False
        
        # Initialize IR sensors
        self.phidget_interface_kit = None
        self.ir0_init = 0
        self.ir1_init = 0
        self.ir2_init = 0
        self.time = 0
        
        # Get configuration
        self.agent_config = agent.agent_config
        self.context_manager = agent.context_manager
        
    def set_up(self):
        """Set up the whiteboard agent and initialize sensors"""
        super().set_up()
        try:
            self._init_phidget()
        except Exception as e:
            logger.error(f"Could not initialize Phidget interface: {e}")
            
    def _init_phidget(self):
        """Initialize the Phidget interface kit"""
        try:
            # This is a placeholder - actual implementation would use Phidget library
            logger.info("Initializing Phidget interface")
            self._calibrate_sensors()
        except Exception as e:
            logger.error(f"Error initializing Phidget: {e}")
            
    def _calibrate_sensors(self):
        """Calibrate the IR sensors"""
        try:
            # Get initial IR values
            self.ir0_init = self._get_sensor_value(0)
            self.ir1_init = self._get_sensor_value(1)
            self.ir2_init = self._get_sensor_value(2)
            
            logger.info(f"Calibrated IR sensors - IR0: {self.ir0_init}, IR1: {self.ir1_init}, IR2: {self.ir2_init}")
        except Exception as e:
            logger.error(f"Error calibrating sensors: {e}")
            
    def _get_sensor_value(self, sensor_index: int) -> float:
        """Get the value from a specific IR sensor"""
        # This is a placeholder - actual implementation would use Phidget library
        try:
            # Simulate reading from Phidget interface
            return 100.0  # Default value for testing
        except Exception as e:
            logger.error(f"Error reading sensor {sensor_index}: {e}")
            return 0.0
            
    def _process_ir_value(self, ir_value: float) -> float:
        """Process raw IR sensor value using the calibration formula"""
        if 80 < ir_value < 490:
            return 9462 / (ir_value - 16.92)
        return 0.0
        
    def run(self):
        """Main run loop for monitoring whiteboard usage"""
        while True:
            try:
                # Get IR sensor values
                ir0 = self._process_ir_value(self._get_sensor_value(0))
                ir1 = self._process_ir_value(self._get_sensor_value(1))
                ir2 = self._process_ir_value(self._get_sensor_value(2))
                
                logger.debug(f"IR Values - IR0: {ir0}, IR1: {ir1}, IR2: {ir2}")
                
                # Check for whiteboard usage
                if ir0 > 30 and ir1 > 30 and ir2 > 30:
                    if (abs(ir0 - self.ir0_init) > 30 or 
                        abs(ir1 - self.ir1_init) > 30 or 
                        abs(ir2 - self.ir2_init) > 30):
                        
                        if not self.current:
                            self.context_manager.update_context(
                                "WhiteboardUsed",
                                True,
                                self.agent_name
                            )
                            
                        # Log sensor usage
                        if abs(ir0 - self.ir0_init) > 30 and ir0 > 30:
                            logger.info(f"IR0 Used: {ir0}")
                        if abs(ir1 - self.ir1_init) > 30 and ir1 > 30:
                            logger.info(f"IR1 Used: {ir1}")
                        if abs(ir2 - self.ir2_init) > 30 and ir2 > 30:
                            logger.info(f"IR2 Used: {ir2}")
                            
                        self.time = 0
                        self.current = True
                    else:
                        if self.time <= 20:
                            self.time += 1
                else:
                    if self.time <= 20:
                        self.time += 1
                        
                # Sleep to prevent excessive CPU usage
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(1)  # Sleep longer on error
                
    def stop(self):
        """Clean up when stopping the agent"""
        try:
            if self.phidget_interface_kit:
                # Close Phidget interface
                logger.info("Closing Phidget interface")
                # Actual implementation would close the Phidget interface here
        except Exception as e:
            logger.error(f"Error stopping agent: {e}")
        finally:
            super().stop() 