# lapras_main.py
import os
import sys
import logging
import importlib
import argparse
import urllib.request
from typing import List, Type

from agent.agent import Agent, LaprasException
from agent.agent_config import AgentConfig
from agent.component import Component
from agent.agent_component import AgentComponent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("LaprasMain")

# Package paths
AGENT_PACKAGE = "lapras.agents."
COMPONENT_PACKAGE = "lapras."

def load_config(config_path: str) -> AgentConfig:
    """
    Load agent configuration from file or URL
    
    Args:
        config_path: Path to configuration file or URL
        
    Returns:
        AgentConfig object
    """
    if config_path.startswith("http"):
        logger.info(f"Loading configuration from URL: {config_path}")
        try:
            with urllib.request.urlopen(config_path) as response:
                return AgentConfig.from_stream(response)
        except Exception as e:
            logger.error(f"Error loading configuration from URL: {e}")
            raise
    else:
        logger.info(f"Loading configuration from file: {config_path}")
        try:
            with open(config_path, 'r') as f:
                return AgentConfig.from_stream(f)
        except Exception as e:
            logger.error(f"Error loading configuration from file: {e}")
            raise

def load_class(class_path: str) -> Type:
    """
    Load a class from its fully qualified name
    
    Args:
        class_path: Fully qualified class name
        
    Returns:
        Class object
    """
    try:
        module_path, class_name = class_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        logger.error(f"Error loading class {class_path}: {e}")
        raise

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LAPRAS Agent Runner")
    parser.add_argument("config", help="Path to configuration file or URL")
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Get agent class name
        agent_class_name = config.get_option("agent_class_name")
        if not agent_class_name:
            logger.error("No agent_class_name specified in configuration")
            sys.exit(1)
        
        # Load agent class
        agent_class_path = AGENT_PACKAGE + agent_class_name
        logger.info(f"Loading agent class: {agent_class_path}")
        agent_class = load_class(agent_class_path)
        
        # Create agent
        agent = Agent(agent_class, config)
        
        # Load additional components
        component_class_names = config.get_option_as_array("component_class_names")
        for component_class_name in component_class_names:
            component_class_path = COMPONENT_PACKAGE + component_class_name
            logger.info(f"Loading component class: {component_class_path}")
            component_class = load_class(component_class_path)
            agent.add_component(component_class)
        
        # Start agent
        logger.info(f"Starting agent: {config.get_agent_name()}")
        agent.start()
        
        # Keep the main thread running
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Agent stopped by user")
        
    except Exception as e:
        logger.error(f"Error starting agent: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()