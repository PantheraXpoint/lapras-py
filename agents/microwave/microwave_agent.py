# lapras/agents/microwave/microwave_agent.py
import logging
from typing import Any

from agent.agent_component import FunctionalityMethod
from middleware.context.context import Context
from middleware.context.context_field import ContextField
from phidget.phidget_sensor_agent import PhidgetSensorAgent

class MicrowaveAgent(PhidgetSensorAgent):
    """
    Agent that monitors the state of a microwave door using a Phidget sensor.
    The sensor value is compared against a threshold to determine if the door is open or closed.
    """
    
    def __init__(self, event_dispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize the flag for door state
        self.flag_open = False
        
        # Create context for microwave state
        self.microwavestate = Context("MicrowaveState", None, self)
        self.microwavestate.set_initial_value("Close")
        
        # Get threshold from config
        try:
            self.threshold = int(agent.get_agent_config().get_option("threshold"))
        except (TypeError, ValueError):
            self.logger.warning("No threshold specified, using default value of 500")
            self.threshold = 500
    
    def set_up(self):
        """Set up the agent"""
        super().set_up()
        self.microwavestate.set_initial_value("Close")
        
        # Force publish the initial state
        self.context_manager.set_publish_as_updated("MicrowaveState")
        
        self.logger.info(f"MicrowaveAgent started with threshold: {self.threshold}")
    
    def value_changed(self, sensor_index: int, sensor_value: int):
        """Handle changes in the sensor value"""
        self.logger.debug(f"Microwave raw value read: {sensor_value}")
        
        # Check if the value crossed the threshold
        if sensor_value >= self.threshold and not self.flag_open:
            self.microwavestate.update_value("Open")
            self.flag_open = True
            self.logger.info("Microwave door opened")
        elif sensor_value < self.threshold and self.flag_open:
            self.microwavestate.update_value("Close")
            self.flag_open = False
            self.logger.info("Microwave door closed")
    
    @FunctionalityMethod(name="ChangeState", description="Manually toggle the microwave door state")
    def change_state(self):
        """Manually toggle the microwave door state"""
        new_state = "Open" if not self.flag_open else "Close"
        self.microwavestate.update_value(new_state)
        self.flag_open = not self.flag_open
        
        self.logger.info(f"Microwave door state manually changed to: {new_state}")
        return f"Microwave state changed to {new_state}"