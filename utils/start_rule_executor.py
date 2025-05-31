#!/usr/bin/env python3

import logging
import sys
import os
import signal
import json
import threading
import time

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lapras_middleware.rule_executor import RuleExecutor 
from lapras_middleware.event import EventDispatcher
from lapras_middleware.context import ContextManager
from lapras_middleware.communicator import MqttCommunicator

class RuleExecutorService:
    def __init__(self):
        self.event_dispatcher = None
        self.mqtt_communicator = None
        self.rule_executor = None
        self.running = False
        self._shutdown_event = threading.Event()
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start the rule executor service."""
        try:
            # Initialize event dispatcher
            self.event_dispatcher = EventDispatcher()
            self.logger.info("Event dispatcher initialized")
            
            # Initialize MQTT communicator
            # self.mqtt_communicator = MqttCommunicator(
            #     event_dispatcher=self.event_dispatcher,
            #     broker="localhost",
            #     port=1883,
            #     client_id="rule_executor"
            # )
            self.logger.info("MQTT communicator initialized")
            
            # Initialize rule executor
            self.rule_executor = RuleExecutor(
                # event_dispatcher=self.event_dispatcher,
                # mqtt_communicator=self.mqtt_communicator
                broker="localhost",
                port=1883
            )
            self.logger.info("Rule executor initialized")
            
            # Load rules
            rules_path = os.path.join(os.path.dirname(__file__), "lapras_middleware/rules/rules.ttl")
            self.rule_executor.load_rules(rules_path)
            self.logger.info(f"Rules loaded from {rules_path}")
            
            # Start components in order
            self.logger.info("Starting event dispatcher...")
            self.event_dispatcher.start()
            self.logger.info("Event dispatcher started")
            
            self.logger.info("Starting rule executor...")
            self.rule_executor.start()
            self.logger.info("Rule executor started")
            
            self.running = True
            self.logger.info("Rule Executor service started and monitoring context updates")
            
        except Exception as e:
            self.logger.error(f"Error starting Rule Executor service: {str(e)}", exc_info=True)
            self.stop()
            raise
            
    def stop(self):
        """Stop the rule executor service."""
        if not self.running:
            return
            
        self.running = False
        self._shutdown_event.set()
        
        # Stop components in reverse order
        if self.rule_executor:
            try:
                self.logger.info("Stopping rule executor...")
                self.rule_executor.stop()
                self.logger.info("Rule executor stopped")
            except Exception as e:
                self.logger.error(f"Error stopping rule executor: {e}")
                
        if self.event_dispatcher:
            try:
                self.logger.info("Stopping event dispatcher...")
                self.event_dispatcher.stop()
                self.logger.info("Event dispatcher stopped")
            except Exception as e:
                self.logger.error(f"Error stopping event dispatcher: {e}")
                
        self.logger.info("Rule Executor service stopped")
        
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
            self.logger.error(f"Error in Rule Executor service: {str(e)}", exc_info=True)
        finally:
            self.stop()

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger = logging.getLogger(__name__)
    logger.info("Received shutdown signal")
    if service:
        service.stop()
    sys.exit(0)

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s] - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize rule executor
        rule_executor = RuleExecutor()
        
        # Load rules from unified rules file
        rule_executor.load_rules("lapras_middleware/rules/rules.ttl")
        logger.info("[RULE_EXECUTOR] Rule executor started")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("[RULE_EXECUTOR] Received keyboard interrupt")
    except Exception as e:
        logger.error(f"[RULE_EXECUTOR] Error in rule executor: {e}")
    finally:
        if 'rule_executor' in locals():
            rule_executor.stop()
        logger.info("[RULE_EXECUTOR] Rule executor stopped")

if __name__ == "__main__":
    main() 