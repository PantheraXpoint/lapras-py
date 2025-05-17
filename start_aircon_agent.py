#!/usr/bin/env python3
import logging
import time
from lapras_agents.aircon_agent import AirconAgent

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s] - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize aircon agent
        agent = AirconAgent(agent_id="aircon")
        logger.info("[AIRCON] Aircon agent started")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("[AIRCON] Received keyboard interrupt")
    except Exception as e:
        logger.error(f"[AIRCON] Error in aircon agent: {e}")
    finally:
        if 'agent' in locals():
            agent.stop()
        logger.info("[AIRCON] Aircon agent stopped")

if __name__ == "__main__":
    main() 