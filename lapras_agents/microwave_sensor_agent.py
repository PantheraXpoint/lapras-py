from lapras_middleware.agent import AgentComponent
from lapras_middleware.event import Event
from lapras_middleware.context import Context, ContextField
from .phidget_sensor_agent import PhidgetSensorAgent, CallbackType
import logging
import time

logger = logging.getLogger(__name__)

class MicrowaveSensorAgent(PhidgetSensorAgent):
    def __init__(self, event_dispatcher, agent):
        super().__init__(event_dispatcher, agent)
        # Mirror Java version's flag
        self._flag_open = False
        
        # Context field similar to Java version
        self.microwave_state = Context("Close")
        
        # Get threshold from config
        self.threshold = int(agent.agent_config.get_option("threshold", "500"))
        
        # Dispatch initialization event
        self.event_dispatcher.dispatch(Event(
            type="microwave_agent_started",
            data={
                "message": "Microwave sensor agent initialized",
                "timestamp": int(time.time() * 1000)
            }
        ))
        logger.info("Microwave sensor agent initialized")

    def set_up(self):
        """Initialize the agent - similar to setUp() in Java version"""
        super().set_up()
        self.microwave_state.set_value("Close")
        logger.info("Microwave sensor agent setup completed")

    def value_changed(self, sensor_index: int, sensor_value: int):
        """Handle sensor value changes - similar to valueChanged() in Java"""
        logger.debug(f"Microwave raw value read: {sensor_value}")
        
        if sensor_value >= self.threshold and not self._flag_open:
            self.microwave_state.update_value("Open")
            self._flag_open = True
            self._dispatch_state_change_event("Open")
        elif sensor_value < self.threshold and self._flag_open:
            self.microwave_state.update_value("Close")
            self._flag_open = False
            self._dispatch_state_change_event("Close")

    def change_state(self):
        """Manual state change functionality - similar to changeState() in Java"""
        new_state = "Open" if not self._flag_open else "Close"
        self.microwave_state.update_value(new_state)
        self._flag_open = not self._flag_open
        self._dispatch_state_change_event(new_state)

    def _dispatch_state_change_event(self, state: str):
        """Helper method to dispatch state change events"""
        self.event_dispatcher.dispatch(Event(
            type="microwave_state_changed",
            data={
                "state": state,
                "timestamp": int(time.time() * 1000)
            }
        ))

    def stop(self):
        """Stop the microwave agent"""
        self.event_dispatcher.dispatch(Event(
            type="microwave_agent_stopped",
            data={
                "message": "Microwave sensor agent stopped",
                "timestamp": int(time.time() * 1000)
            }
        ))
        logger.info("Microwave sensor agent stopped")
        super().stop() 