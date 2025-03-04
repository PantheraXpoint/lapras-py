# lapras/agent/agent.py
import logging
import time
import locale
import importlib
import inspect
from typing import Dict, List, Type, Optional, Any

from agent.agent_config import AgentConfig
from agent.component import Component
from agent.agent_component import AgentComponent
from communicator.mqtt_communicator import MqttCommunicator
from context.context_manager import ContextManager
from functionality.functionality_executor import FunctionalityExecutor
from event.event_dispatcher import EventDispatcher
from event.event import Event

class LaprasException(Exception):
    """Base exception for LAPRAS"""
    pass

class Agent:
    def __init__(self, agent_class: Type[AgentComponent], agent_config: AgentConfig):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set locale
        locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
        
        self.start_time = 0
        self.agent_config = agent_config
        self.event_dispatcher = EventDispatcher()
        
        self.components: List[Component] = []
        
        # Initialize core components
        try:
            self.mqtt_communicator = MqttCommunicator(self.event_dispatcher, self)
            self.components.append(self.mqtt_communicator)
        except Exception as e:
            self.logger.error(f"Cannot initialize MqttCommunicator: {e}")
            raise LaprasException("Failed to initialize the agent") from e
        
        self.context_manager = ContextManager(self.event_dispatcher, self)
        self.components.append(self.context_manager)
        
        self.functionality_executor = FunctionalityExecutor(self.event_dispatcher, self)
        self.components.append(self.functionality_executor)
        
        # Initialize action manager, task manager, and user manager
        # These would be implemented in similar fashion to the other components
        self.action_manager = None
        self.task_manager = None
        self.user_manager = None
        
        # Add the agent component
        self.add_component(agent_class)
        self.agent_component = self.get_component(agent_class)
    
    @classmethod
    def from_config_file(cls, agent_class: Type[AgentComponent], config_file_path: str) -> 'Agent':
        """Create an agent from a configuration file"""
        try:
            agent_config = AgentConfig.from_file(config_file_path)
            return cls(agent_class, agent_config)
        except FileNotFoundError as e:
            raise LaprasException(f"Config file not found: {config_file_path}") from e
    
    def add_component(self, component_class: Type[Component]):
        """Add a component to the agent"""
        try:
            component = component_class(self.event_dispatcher, self)
            self.components.append(component)
        except Exception as e:
            self.logger.error(f"Cannot instantiate component {component_class.__name__}: {e}")
            raise LaprasException(f"Failed to add component {component_class.__name__}") from e
    
    def start(self):
        """Start the agent and all its components"""
        self.start_time = int(time.time() * 1000)
        
        # Start the event dispatcher
        self.event_dispatcher.start()
        
        # Start all components
        for component in self.components:
            component.start()
    
    def get_component(self, component_class: Type[Component]) -> Optional[Component]:
        """Get a component by its class"""
        for component in self.components:
            if isinstance(component, component_class):
                return component
        return None
    
    def get_agent_component(self) -> AgentComponent:
        """Get the agent component"""
        return self.agent_component
    
    def get_mqtt_communicator(self) -> MqttCommunicator:
        """Get the MQTT communicator"""
        return self.mqtt_communicator
    
    def get_agent_config(self) -> AgentConfig:
        """Get the agent configuration"""
        return self.agent_config
    
    def get_context_manager(self) -> ContextManager:
        """Get the context manager"""
        return self.context_manager
    
    def get_functionality_executor(self) -> FunctionalityExecutor:
        """Get the functionality executor"""
        return self.functionality_executor
    
    def get_start_time(self) -> int:
        """Get the agent start time in milliseconds"""
        return self.start_time
    
    def get_uptime(self) -> int:
        """Get the agent uptime in milliseconds"""
        return int(time.time() * 1000) - self.get_start_time()