# lapras/agents/phidget/phidget_sensor_agent.py
import logging
import time
from agent.agent_component import AgentComponent

class PhidgetSensorAgent(AgentComponent):
    """Base class for Phidget sensor agents"""

    def __init__(self, event_dispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sensor_name = agent.get_agent_config().get_option("sensor_name")
        self.sensor_value = 0
        
    def run(self):
        """Main agent loop - simulate sensor readings in base class"""
        self.logger.info(f"PhidgetSensorAgent started: {self.sensor_name}")
        
        try:
            while True:
                # In a real implementation, you would read from the Phidget hardware
                # For simulation, we'll just generate random values
                new_value = self._read_sensor_value()
                
                if new_value != self.sensor_value:
                    self.sensor_value = new_value
                    self.value_changed(0, new_value)  # Simulate a value change event
                    
                time.sleep(1)  # Poll every second
                
        except Exception as e:
            self.logger.error(f"Error in sensor loop: {e}")
            
    def _read_sensor_value(self):
        """
        Override in real implementation to read from hardware
        In base class, just returns a simple simulated value
        """
        import random
        return random.randint(0, 1000)  # Simulate a raw sensor value
        
    def value_changed(self, sensor_index, sensor_value):
        """
        Called when a sensor value changes.
        To be implemented by subclasses.
        """
        pass