import time
import logging
from lapras_middleware.agent import AgentComponent
from lapras_middleware.event import Event

logger = logging.getLogger(__name__)

class SoundAlertAgent(AgentComponent):
    def __init__(self, event_dispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.noise_threshold = 10.0
        self.current_status = "quiet"
        
        # Subscribe to context updates
        self.subscribe_event("CONTEXT_UPDATED")
        logger.info("Sound alert agent created")
        
    def start(self):
        """Start the sound alert agent."""
        super().start()
        
        # Initialize context
        self.agent.context_manager.update_context(
            "sound/status",
            self.current_status,
            "sound_alert_agent",
            int(time.time() * 1000)
        )
        
        # Dispatch initialization event
        self.event_dispatcher.dispatch(Event(
            type="AGENT_INITIALIZED",
            data={
                "agent": "sound_alert_agent",
                "timestamp": int(time.time() * 1000)
            }
        ))
        logger.info("Sound alert agent initialized")

    def handle_event(self, event: Event):
        """Handle incoming events."""
        if event.type == "CONTEXT_UPDATED":
            try:
                context = event.data.get("context")
                if context == "sound/level":
                    sound_level = event.data.get("value", 0.0)
                    self.check_sound_level(sound_level)
            except Exception as e:
                logger.error(f"Error handling context update: {e}")

    def check_sound_level(self, level: float):
        """Check sound level and update status accordingly."""
        try:
            new_status = "noise" if level > self.noise_threshold else "quiet"
            
            if new_status != self.current_status:
                self.current_status = new_status
                self.agent.context_manager.update_context(
                    "sound/status",
                    self.current_status,
                    "sound_alert_agent",
                    int(time.time() * 1000)
                )
                logger.info(f"Sound status changed to: {new_status}")
                
                # Dispatch alert event
                self.event_dispatcher.dispatch(Event(
                    type="SOUND_ALERT",
                    data={
                        "status": new_status,
                        "level": level,
                        "timestamp": int(time.time() * 1000)
                    }
                ))
        except Exception as e:
            logger.error(f"Error checking sound level: {e}")
            raise

    def stop(self):
        """Clean up when stopping the agent."""
        logger.info("Stopping sound alert agent")
        self.agent.context_manager.update_context(
            "sound/status",
            "quiet",
            "sound_alert_agent",
            int(time.time() * 1000)
        )
        super().stop()

def test_sound_levels(agent, sound_agent):
    """Test various sound levels and verify alert agent response."""
    logger.info("Testing sound levels and alert responses...")
    
    test_sequence = [
        (5.0, "quiet - below threshold"),
        (8.0, "still quiet - below threshold"),
        (12.0, "noise - above threshold"),
        # ...
    ]
    
    for level, description in test_sequence:
        logger.info(f"Testing sound level {level}: {description}")
        agent.event_dispatcher.dispatch(Event(
            type="SOUND_UPDATE",
            data={
                "level": level,
                "timestamp": int(time.time() * 1000)
            }
        ))
        time.sleep(2)  # Wait for processing and alert response

def test_alert_transitions(agent, sound_agent):
    """Test transitions between quiet and noise states."""
    logger.info("Testing alert state transitions...")
    
    # Test transition from quiet to noise
    logger.info("Testing quiet to noise transition...")
    agent.event_dispatcher.dispatch(Event(
        type="SOUND_UPDATE",
        data={
            "level": 5.0,  # Start quiet
            "timestamp": int(time.time() * 1000)
        }
    ))
    time.sleep(2)
    
    agent.event_dispatcher.dispatch(Event(
        type="SOUND_UPDATE",
        data={
            "level": 12.0,  # Transition to noise
            "timestamp": int(time.time() * 1000)
        }
    ))
    time.sleep(2)
    
    # Test transition from noise to quiet
    logger.info("Testing noise to quiet transition...")
    agent.event_dispatcher.dispatch(Event(
        type="SOUND_UPDATE",
        data={
            "level": 15.0,  # Start noisy
            "timestamp": int(time.time() * 1000)
        }
    ))
    time.sleep(2)
    
    agent.event_dispatcher.dispatch(Event(
        type="SOUND_UPDATE",
        data={
            "level": 8.0,  # Transition to quiet
            "timestamp": int(time.time() * 1000)
        }
    ))
    time.sleep(2) 