# lapras/agents/microwave/microwave_agent.py
from phidget.phidget_sensor_agent import PhidgetSensorAgent
from context.context import Context
from context.context_field import ContextField
from agent.agent_component import FunctionalityMethod

class MicrowaveAgent(PhidgetSensorAgent):
    """Agent that monitors the state of a microwave door"""
    
    # Define context fields
    microwavestate = Context("MicrowaveState", None, None)  # Will be properly initialized later in __init__
    
    def __init__(self, event_dispatcher, agent):
        super().__init__(event_dispatcher, agent)
        
        # Initialize context and fix the reference
        self.microwavestate.agent_component = self
        
        # Get threshold from config
        self.threshold = int(agent.get_agent_config().get_option("threshold") or "500")
        self.flag_open = False
        
        # Set initial state
        self.microwavestate.set_initial_value("Close")
    
    def set_up(self):
        super().set_up()
        self.microwavestate.set_initial_value("Close")
    
    def value_changed(self, sensor_index, sensor_value):
        """Handle changes in the sensor value"""
        self.logger.debug(f"Microwave raw value read: {sensor_value}")
        
        if sensor_value >= self.threshold and not self.flag_open:
            self.microwavestate.update_value("Open")
            self.flag_open = True
        elif sensor_value < self.threshold and self.flag_open:
            self.microwavestate.update_value("Close")
            self.flag_open = False
    
    @FunctionalityMethod(name="ChangeState", description="Manually toggle the microwave door state")
    def change_state(self):
        """Manually toggle the microwave door state"""
        self.microwavestate.update_value("Open" if not self.flag_open else "Close")
        self.flag_open = not self.flag_open
        return f"Microwave state changed to {'Open' if self.flag_open else 'Close'}"