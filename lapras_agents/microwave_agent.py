from lapras_middleware.agent import AgentComponent
from lapras_middleware.event import Event
import time
import logging

logger = logging.getLogger(__name__)

class MicrowaveAgent(AgentComponent):
    def __init__(self, event_dispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.subscribe_event("microwave_started")
        self.subscribe_event("microwave_stopped")
        # Dispatch start event
        self.event_dispatcher.dispatch(Event(
            type="microwave_agent_started",
            data={
                "message": "Microwave agent initialized",
                "timestamp": int(time.time() * 1000)
            }
        ))
        logger.info("Microwave agent initialized")
        
    def handle_event(self, event: Event) -> bool:
        if event.type == "microwave_started":
            duration = event.data.get("duration", 0)
            logger.info(f"Microwave started for {duration} seconds")
            # Notify user about microwave duration
            self.event_dispatcher.dispatch(Event(
                type="user_notification",
                data={
                    "message": f"Microwave started for {duration} seconds",
                    "timestamp": int(time.time() * 1000)
                }
            ))
            return True
        elif event.type == "microwave_stopped":
            logger.info("Microwave stopped")
            self.event_dispatcher.dispatch(Event(
                type="user_notification",
                data={
                    "message": "Microwave stopped",
                    "timestamp": int(time.time() * 1000)
                }
            ))
            return True
        return False
        
    def stop(self) -> None:
        """Stop the microwave agent."""
        self.event_dispatcher.dispatch(Event(
            type="microwave_agent_stopped",
            data={
                "message": "Microwave agent stopped",
                "timestamp": int(time.time() * 1000)
            }
        ))
        logger.info("Microwave agent stopped")
        super().stop() 