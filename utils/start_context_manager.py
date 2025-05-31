#!/usr/bin/env python3
import logging
import time
from lapras_middleware.context import ContextManager

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s] - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize context manager
        context_manager = ContextManager()
        logger.info("[CONTEXT_MANAGER] Context manager started")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("[CONTEXT_MANAGER] Received keyboard interrupt")
    except Exception as e:
        logger.error(f"[CONTEXT_MANAGER] Error in context manager: {e}")
    finally:
        if 'context_manager' in locals():
            context_manager.stop()
        logger.info("[CONTEXT_MANAGER] Context manager stopped")

if __name__ == "__main__":
    main() 