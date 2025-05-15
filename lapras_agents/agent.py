import logging
import sys
import json
from typing import List, Type, Dict, Any
from urllib.request import urlopen
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)
)
logger = logging.getLogger(__name__)

class AgentConfig:
    def __init__(self, config_data: Dict[str, Any]):
        self.config = config_data
        
    @classmethod
    def from_stream(cls, stream):
        config_data = json.load(stream)
        return cls(config_data)
        
    def get_option(self, key: str) -> str:
        return self.config.get(key)
        
    def get_option_as_array(self, key: str) -> List[str]:
        value = self.config.get(key, [])
        return value if isinstance(value, list) else [value]
        
    @property
    def agent_name(self) -> str:
        return self.config.get('agent_name', 'Unknown')

class Component:
    def __init__(self, event_dispatcher, agent):
        self.event_dispatcher = event_dispatcher
        self.agent = agent
        
    def start(self):
        pass
        
    def stop(self):
        pass

class AgentComponent(Component):
    def __init__(self, event_dispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.subscribed_events = set()
        
    def subscribe_event(self, event_type: str):
        self.subscribed_events.add(event_type)
        
    def handle_event(self, event) -> bool:
        return True
        
    def run(self):
        pass

class Agent:
    def __init__(self, agent_component_class: Type[AgentComponent], config: AgentConfig):
        self.agent_component_class = agent_component_class
        self.config = config
        self.components: List[Component] = []
        self.event_dispatcher = None  # This would be implemented based on your event system
        
    def add_component(self, component_class: Type[Component]):
        component = component_class(self.event_dispatcher, self)
        self.components.append(component)
        
    def start(self):
        for component in self.components:
            component.start()

def main():
    if len(sys.argv) < 2:
        logger.error("Configuration file path must be specified in the first argument")
        sys.exit(1)
        
    config_path = sys.argv[1]
    agent_config = None
    
    try:
        if config_path.startswith(('http://', 'https://')):
            logger.debug(f"Loading configuration file from web at {config_path}")
            with urlopen(config_path) as response:
                agent_config = AgentConfig.from_stream(response)
        else:
            logger.debug(f"Loading configuration file at {config_path}")
            with open(config_path) as f:
                agent_config = AgentConfig.from_stream(f)
                
        agent_class_name = f"lapras_agents.{agent_config.get_option('agent_class_name')}"
        component_names = agent_config.get_option_as_array('component_class_names')
        
        # Import and instantiate the agent
        module_name, class_name = agent_class_name.rsplit('.', 1)
        module = __import__(module_name, fromlist=[class_name])
        agent_class = getattr(module, class_name)
        
        agent = Agent(agent_class, agent_config)
        
        # Add components
        for component_name in component_names:
            full_component_name = f"lapras.{component_name}"
            module_name, class_name = full_component_name.rsplit('.', 1)
            module = __import__(module_name, fromlist=[class_name])
            component_class = getattr(module, class_name)
            agent.add_component(component_class)
            
        logger.debug(f"Starting {agent_config.agent_name}")
        agent.start()
        
    except Exception as e:
        logger.error(f"An error occurred while launching the agent: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 