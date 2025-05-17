import logging
import time
import random
from lapras_middleware.agent import Agent

logger = logging.getLogger(__name__)

class AirconAgent(Agent):
    """Air conditioner agent that monitors distance and controls power state."""
    
    def __init__(self, agent_id: str = "aircon", mqtt_broker: str = "localhost", mqtt_port: int = 1883):
        """Initialize the air conditioner agent."""
        super().__init__(agent_id, mqtt_broker, mqtt_port)
        
        # Initialize local state
        with self.state_lock:
            self.local_state.update({
                "distance": 0.0,
                "power": "off"
            })
        
        logger.info("[AIRCON] Air conditioner agent initialized")
    
    def perception(self) -> None:
        """Update local state based on sensor readings."""
        try:
            # Simulate distance measurement (replace with actual sensor reading)
            distance = random.uniform(0, 1)
            
            with self.state_lock:
                self.local_state["distance"] = distance
                logger.info(f"[AIRCON] Updated distance to {distance}m")
                
        except Exception as e:
            logger.error(f"[AIRCON] Error in perception: {e}")
    
    def stop(self) -> None:
        """Stop the air conditioner agent."""
        logger.info("[AIRCON] Stopping air conditioner agent...")
        # Update power state to off before stopping
        with self.state_lock:
            self.local_state["power"] = "off"
        super().stop()
        logger.info("[AIRCON] Air conditioner agent stopped") 