import time
import logging
import random
from lapras_middleware.agent import AgentComponent
from lapras_middleware.event import Event

logger = logging.getLogger(__name__)

class SoundAgent(AgentComponent):
    def __init__(self, event_dispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.sound_level = 0.0
        
        # Subscribe to events
        self.subscribe_event("SOUND_UPDATE")
        logger.info("Sound agent created")
        
    def start(self):
        """Start the sound agent."""
        super().start()
        
        # Initialize context
        self.agent.context_manager.update_context(
            "sound/level",
            self.sound_level,
            "sound_agent",
            int(time.time() * 1000)
        )
        
        # Dispatch initialization event
        self.event_dispatcher.dispatch(Event(
            type="AGENT_INITIALIZED",
            data={
                "agent": "sound_agent",
                "timestamp": int(time.time() * 1000)
            }
        ))
        logger.info("Sound agent initialized")

    def handle_event(self, event: Event):
        """Handle incoming events."""
        if event.type == "SOUND_UPDATE":
            try:
                new_level = event.data.get("level", 0.0)
                self.update_sound_level(new_level)
            except Exception as e:
                logger.error(f"Error handling sound update: {e}")

    def update_sound_level(self, level: float):
        """Update the sound level in the context."""
        try:
            if level < 0:
                raise ValueError("Sound level cannot be negative")
            
            self.sound_level = level
            self.agent.context_manager.update_context(
                "sound/level",
                self.sound_level,
                "sound_agent",
                int(time.time() * 1000)
            )
            logger.info(f"Updated sound level to {level}")
            
            # Dispatch event for the update
            self.event_dispatcher.dispatch(Event(
                type="CONTEXT_UPDATED",
                data={
                    "context": "sound/level",
                    "value": level,
                    "timestamp": int(time.time() * 1000)
                }
            ))
        except Exception as e:
            logger.error(f"Error updating sound level: {e}")
            raise

    def stop(self):
        """Clean up when stopping the agent."""
        logger.info("Stopping sound agent")
        self.agent.context_manager.update_context(
            "sound/level",
            0.0,
            "sound_agent",
            int(time.time() * 1000)
        )
        super().stop() 