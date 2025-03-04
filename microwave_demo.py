# microwave_demo.py
import time
import logging
import threading
import argparse
from typing import Optional

from agent.agent import Agent
from agent.agent_config import AgentConfig
from agents.microwave.microwave_agent import MicrowaveAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("MicrowaveDemo")

class SensorSimulator:
    """Simulates sensor values for testing"""
    
    def __init__(self, agent: Agent, threshold: int):
        self.agent = agent
        self.threshold = threshold
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the simulator"""
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop the simulator"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
    
    def _run(self):
        """Main simulator loop"""
        try:
            logger.info("Sensor simulator started")
            
            # Get the PhidgetSensorAgent from the agent
            sensor_agent = self.agent.get_agent_component()
            
            # Start with door closed (value below threshold)
            value = self.threshold - 100
            sensor_agent.set_sensor_value(0, value)
            
            while self.running:
                # Get user input for simulation
                choice = input(
                    "\nSimulation Options:\n"
                    "1. Open Door (set value above threshold)\n"
                    "2. Close Door (set value below threshold)\n"
                    "3. Invoke ChangeState functionality\n"
                    "4. Get current state\n"
                    "5. Exit\n"
                    "Enter choice (1-5): "
                )
                
                if choice == "1":
                    # Simulate door opening
                    value = self.threshold + 100
                    logger.info(f"Setting sensor value to {value} (above threshold)")
                    sensor_agent.set_sensor_value(0, value)
                
                elif choice == "2":
                    # Simulate door closing
                    value = self.threshold - 100
                    logger.info(f"Setting sensor value to {value} (below threshold)")
                    sensor_agent.set_sensor_value(0, value)
                
                elif choice == "3":
                    # Invoke ChangeState functionality
                    logger.info("Invoking ChangeState functionality")
                    functionality_executor = self.agent.get_functionality_executor()
                    functionality_executor.invoke_functionality_by_name("ChangeState", [])
                
                elif choice == "4":
                    # Get current state
                    microwave_agent = self.agent.get_agent_component()
                    state = microwave_agent.microwavestate.get_value()
                    logger.info(f"Current microwave state: {state}")
                
                elif choice == "5":
                    logger.info("Exiting simulator")
                    self.running = False
                    break
                
                else:
                    logger.warning("Invalid choice, try again")
        
        except Exception as e:
            logger.error(f"Error in simulator: {e}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Microwave Sensor Demo")
    parser.add_argument("--broker", default="localhost:1883", help="MQTT broker address")
    parser.add_argument("--threshold", type=int, default=500, help="Sensor threshold value")
    args = parser.parse_args()
    
    try:
        # Create agent configuration
        config = AgentConfig("MicrowaveMonitor")
        config.set_broker_address(args.broker)
        config.set_place_name("kitchen")
        config.set_option("threshold", str(args.threshold))
        
        # Create and start the agent
        agent = Agent(MicrowaveAgent, config)
        agent.start()
        
        logger.info(f"MicrowaveAgent started with threshold: {args.threshold}")
        logger.info("MQTT broker: " + args.broker)
        
        # Start the sensor simulator
        simulator = SensorSimulator(agent, args.threshold)
        simulator.start()
        
        # Wait for the simulator to finish
        try:
            while simulator.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Interrupted, stopping...")
        finally:
            simulator.stop()
            logger.info("Demo stopped")
    
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()