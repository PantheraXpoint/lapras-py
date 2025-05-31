#!/usr/bin/env python3
import logging
import time
from lapras_agents.microwave_agent import MicrowaveAgent # Import your MicrowaveAgent

def main():
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s] - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    microwave_agent_instance = None
    try:
        logger.info("[MAIN_MICROWAVE] Creating MicrowaveAgent instance...")
        # Ensure constants LIGHT_SENSOR_SERIAL_NUMBER and LIGHT_SENSOR_CHANNEL
        # are correctly set inside microwave_agent.py
        microwave_agent_instance = MicrowaveAgent(agent_id="microwave_1") # Example ID
        logger.info("[MAIN_MICROWAVE] MicrowaveAgent created.")
        
        logger.info("[MAIN_MICROWAVE] Entering main loop to keep script alive (Ctrl+C to exit)...")
        while True:
            if hasattr(microwave_agent_instance, 'running') and not microwave_agent_instance.running:
                logger.info("[MAIN_MICROWAVE] Agent 'running' flag is False. Exiting main loop.")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("[MAIN_MICROWAVE] Received keyboard interrupt. Stopping agent...")
    except Exception as e:
        logger.error(f"[MAIN_MICROWAVE] Error in main execution: {e}")
        import traceback
        logger.error(traceback.format_exc()) 
    finally:
        logger.info("[MAIN_MICROWAVE] Finally block reached.")
        if 'microwave_agent_instance' in locals() and microwave_agent_instance is not None:
            logger.info("[MAIN_MICROWAVE] Calling microwave_agent_instance.stop()...")
            microwave_agent_instance.stop()
        logger.info("[MAIN_MICROWAVE] Application finished.")

if __name__ == "__main__":
    print("Reminder: Ensure Phidget SN and Channel for the LIGHT SENSOR are correctly set in microwave_agent.py!")
    main()