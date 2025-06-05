#!/usr/bin/env python3
import logging
import time
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lapras_agents.light_hue_agent import LightHueAgent

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s] - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize aircon virtual agent
        agent = LightHueAgent(agent_id="hue_light", decision_window=2)
        logger.info("[HUE] HUE virtual agent initialized and started")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("[HUE] Received keyboard interrupt")
    except Exception as e:
        logger.error(f"[HUE] Error in HUE virtual agent: {e}")
    finally:
        if 'agent' in locals():
            agent.stop()
        logger.info("[HUE] HUE virtual agent stopped")

if __name__ == "__main__":
    main()