import logging
import time
from typing import List, Type, Optional, Dict, Any, Set, TYPE_CHECKING
from dataclasses import dataclass
from pathlib import Path
import json
import locale
from datetime import datetime

from .action import ActionManager
from .communicator import MqttCommunicator
from .context import ContextManager
from .event import EventDispatcher, Event
from .functionality import FunctionalityExecutor
from .task import TaskManager
from .user import UserManager
from .exceptions import LaprasException
from .component import Component

if TYPE_CHECKING:
    from .agent import AgentComponent

logger = logging.getLogger(__name__)

@dataclass
class AgentConfig:
    """Configuration for an agent instance."""
    config_data: Dict[str, Any]
    
    @classmethod
    def from_stream(cls, stream) -> 'AgentConfig':
        """Create an AgentConfig from a file-like stream."""
        config_data = json.load(stream)
        return cls(config_data=config_data)
    
    def get_option(self, key: str, default: Any = None) -> Any:
        """Get a configuration option value."""
        return self.config_data.get(key, default)
    
    def get_option_as_array(self, key: str) -> List[str]:
        """Get a configuration option as an array."""
        value = self.config_data.get(key, [])
        return value if isinstance(value, list) else [value]
    
    @property
    def agent_name(self) -> str:
        """Get the agent name from configuration."""
        return self.config_data.get('agent_name', 'Unknown')

class Agent:
    """Main agent class that coordinates all components and functionality."""
    
    def __init__(self, agent_class: Type['AgentComponent'], config: AgentConfig):
        """Initialize the agent with a specific agent component class and configuration."""
        # Set up logging and locale
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
        
        self.agent_config = config
        self.start_time: Optional[int] = None
        self.components: List[Component] = []
        
        # Initialize event dispatcher
        self.event_dispatcher = EventDispatcher()
        
        try:
            # Initialize core components
            self.mqtt_communicator = MqttCommunicator(self.event_dispatcher, self)
            self.components.append(self.mqtt_communicator)
            
            self.context_manager = ContextManager(self.event_dispatcher, self)
            self.components.append(self.context_manager)
            
            self.functionality_executor = FunctionalityExecutor(self.event_dispatcher, self)
            self.components.append(self.functionality_executor)
            
            self.action_manager = ActionManager(self.event_dispatcher, self)
            self.components.append(self.action_manager)
            
            self.task_manager = TaskManager(self.event_dispatcher, self)
            self.components.append(self.task_manager)
            
            self.user_manager = UserManager(self.event_dispatcher, self)
            self.components.append(self.user_manager)
            
            # Add the main agent component
            self.add_component(agent_class)
            self.agent_component = self.get_component(agent_class)
            
        except Exception as e:
            logger.error("Failed to initialize the agent", exc_info=True)
            raise LaprasException("Failed to initialize the agent") from e
    
    def add_component(self, component_class: Type[Component]) -> None:
        """Add a new component to the agent."""
        try:
            component = component_class(self.event_dispatcher, self)
            self.components.append(component)
        except Exception as e:
            logger.error(f"Cannot instantiate component {component_class.__name__}", exc_info=True)
            raise LaprasException("Failed to add a component") from e
    
    def start(self) -> None:
        """Start the agent and all its components."""
        self.start_time = int(time.time() * 1000)  # Current time in milliseconds
        
        self.event_dispatcher.start()
        
        for component in self.components:
            component.start()
    
    def get_component(self, component_class: Type[Component]) -> Optional[Component]:
        """Get a component instance by its class."""
        for component in self.components:
            if isinstance(component, component_class):
                return component
        return None
    
    @property
    def agent_component(self) -> 'AgentComponent':
        """Get the main agent component."""
        return self._agent_component
    
    @agent_component.setter
    def agent_component(self, value: 'AgentComponent'):
        self._agent_component = value
    
    @property
    def mqtt_communicator(self) -> MqttCommunicator:
        """Get the MQTT communicator instance."""
        return self._mqtt_communicator
    
    @mqtt_communicator.setter
    def mqtt_communicator(self, value: MqttCommunicator):
        self._mqtt_communicator = value
    
    @property
    def agent_config(self) -> AgentConfig:
        """Get the agent configuration."""
        return self._agent_config
    
    @agent_config.setter
    def agent_config(self, value: AgentConfig):
        self._agent_config = value
    
    @property
    def functionality_executor(self) -> FunctionalityExecutor:
        """Get the functionality executor instance."""
        return self._functionality_executor
    
    @functionality_executor.setter
    def functionality_executor(self, value: FunctionalityExecutor):
        self._functionality_executor = value
    
    @property
    def context_manager(self) -> ContextManager:
        """Get the context manager instance."""
        return self._context_manager
    
    @context_manager.setter
    def context_manager(self, value: ContextManager):
        self._context_manager = value
    
    @property
    def action_manager(self) -> ActionManager:
        """Get the action manager instance."""
        return self._action_manager
    
    @action_manager.setter
    def action_manager(self, value: ActionManager):
        self._action_manager = value
    
    @property
    def user_manager(self) -> UserManager:
        """Get the user manager instance."""
        return self._user_manager
    
    @user_manager.setter
    def user_manager(self, value: UserManager):
        self._user_manager = value
    
    @property
    def start_time(self) -> Optional[int]:
        """Get the agent start time."""
        return self._start_time
    
    @start_time.setter
    def start_time(self, value: Optional[int]):
        self._start_time = value
    
    @property
    def uptime(self) -> int:
        """Get the agent uptime in milliseconds."""
        if self.start_time is None:
            return 0
        return int(time.time() * 1000) - self.start_time
    
    @property
    def task_manager(self) -> TaskManager:
        """Get the task manager instance."""
        return self._task_manager
    
    @task_manager.setter
    def task_manager(self, value: TaskManager):
        self._task_manager = value

class AgentComponent(Component):
    """Base class for agent-specific components."""
    
    def __init__(self, event_dispatcher: EventDispatcher, agent: Agent):
        """Initialize an agent component."""
        super().__init__(event_dispatcher, agent)
        self.subscribed_events: Set[str] = set()
        
    def subscribe_event(self, event_type: str) -> None:
        """Subscribe to an event type."""
        self.subscribed_events.add(event_type)
        self.event_dispatcher.subscribe(self, event_type)
        
    def handle_event(self, event: Event) -> bool:
        """Handle an event. Override this method in subclasses."""
        return True
        
    def run(self) -> None:
        """Main run loop for the agent component. Override this method in subclasses."""
        pass 