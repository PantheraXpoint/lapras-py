#!/usr/bin/env python3
import logging
import time
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lapras_agents.infrared_sensor_agent import InfraredSensorAgent

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s] - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize infrared sensor agent
        agent = InfraredSensorAgent(
            sensor_id="infrared_1",
            virtual_agent_id="aircon"
        )
        logger.info("[INFRARED_SENSOR] Infrared sensor agent initialized and started")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("[INFRARED_SENSOR] Received keyboard interrupt")
    except Exception as e:
        logger.error(f"[INFRARED_SENSOR] Error in infrared sensor agent: {e}")
    finally:
        if 'agent' in locals():
            agent.stop()
        logger.info("[INFRARED_SENSOR] Infrared sensor agent stopped")

if __name__ == "__main__":
    main() 