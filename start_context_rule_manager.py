#!/usr/bin/env python3

import logging
import sys
import os
import signal
import time
import threading

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lapras_middleware.context_rule_manager import ContextRuleManager

class ContextRuleService:
    """Service that runs the combined context rule manager."""
    
    def __init__(self):
        self.context_rule_manager = None
        self.running = False
        self._shutdown_event = threading.Event()
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start the context rule service."""
        try:
            # Initialize context rule manager
            self.context_rule_manager = ContextRuleManager(
                mqtt_broker="143.248.57.73",
                mqtt_port=1883
            )
            self.logger.info("Context rule manager initialized")
            
            # Load rules from unified rules file
            rules_path = os.path.join(os.path.dirname(__file__), "lapras_middleware/rules/rules.ttl")
            self.context_rule_manager.load_rules(rules_path)
            self.logger.info(f"Rules loaded from {rules_path}")
            
            self.running = True
            self.logger.info("Context Rule service started and monitoring agent state updates")
            
        except Exception as e:
            self.logger.error(f"Error starting Context Rule service: {str(e)}", exc_info=True)
            self.stop()
            raise
            
    def stop(self):
        """Stop the context rule service."""
        if not self.running:
            return
            
        self.running = False
        self._shutdown_event.set()
        
        if self.context_rule_manager:
            try:
                self.logger.info("Stopping context rule manager...")
                self.context_rule_manager.stop()
                self.logger.info("Context rule manager stopped")
            except Exception as e:
                self.logger.error(f"Error stopping context rule manager: {e}")
                
        self.logger.info("Context Rule service stopped")
        
    def run(self):
        """Run the service until shutdown signal is received."""
        try:
            self.start()
            
            # Keep the main thread alive until shutdown signal
            while not self._shutdown_event.is_set():
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Error in Context Rule service: {str(e)}", exc_info=True)
        finally:
            self.stop()

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger = logging.getLogger(__name__)
    logger.info("Received shutdown signal")
    if 'service' in globals():
        service.stop()
    sys.exit(0)

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s] - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize and run context rule manager
        context_rule_manager = ContextRuleManager()
        
        # Load rules from unified rules file
        context_rule_manager.load_rules("lapras_middleware/rules/rules.ttl")
        logger.info("[CONTEXT_RULE_MANAGER] Context rule manager started")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("[CONTEXT_RULE_MANAGER] Received keyboard interrupt")
    except Exception as e:
        logger.error(f"[CONTEXT_RULE_MANAGER] Error in context rule manager: {e}")
    finally:
        if 'context_rule_manager' in locals():
            context_rule_manager.stop()
        logger.info("[CONTEXT_RULE_MANAGER] Context rule manager stopped")

if __name__ == "__main__":
    main() 