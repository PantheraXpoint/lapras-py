import logging
import locale
import time
from typing import List, Type, Optional, TYPE_CHECKING, TypeVar

from .core import Component
from .config import AgentConfig
from events.events import EventDispatcher
from .exceptions import LaprasException
from .utils.resources import Resource

if TYPE_CHECKING:
    from .components.agent_component import AgentComponent
    from .components.communicator.mqtt import MqttCommunicator
    from .components.context.context import ContextManager
    from .components.functionality.functionality import FunctionalityExecutor

logger = logging.getLogger(__name__)
T = TypeVar('T', bound='Agent')


class Agent:
    def __init__(self, agent_class: Type['AgentComponent'], config_path: str = None, config: AgentConfig = None):
        self.start_time: float = 0
        
        if config_path:
            self.config = AgentConfig.from_stream(Resource.get_stream(config_path))
        elif config:
            self.config = config
        else:
            raise LaprasException("Either config_path or config must be provided")

        locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
        
        self.event_dispatcher = EventDispatcher()
        self.components: List[Component] = []

        try:
            from .components import (
                MqttCommunicator, ContextManager, FunctionalityExecutor
            )
            
            self.mqtt_communicator = MqttCommunicator(self.event_dispatcher, self)
            self.mqtt_communicator.initialize()
            self.components.append(self.mqtt_communicator)
            
            self.context_manager = ContextManager(self.event_dispatcher, self)
            self.context_manager.initialize()
            self.components.append(self.context_manager)

            self.functionality_executor = FunctionalityExecutor(self.event_dispatcher, self)
            self.functionality_executor.initialize()
            self.components.append(self.functionality_executor)
            
        except Exception as e:
            logger.error("Failed to initialize core components", exc_info=e)
            raise LaprasException("Failed to initialize the agent", e)

        self.add_component(agent_class)
        self.agent_component = self.get_component(agent_class)

    def add_component(self, component_class: Type[Component]) -> None:
        try:
            component = component_class(self.event_dispatcher, self)
            component.initialize()
            self.components.append(component)
        except Exception as e:
            logger.error(f"Cannot instantiate component {component_class.__name__}", exc_info=e)
            raise LaprasException("Failed to add a component", e)

    def get_component(self, component_class: Type[T]) -> Optional[T]:
        return next((c for c in self.components if isinstance(c, component_class)), None)

    def start(self) -> None:
        self.start_time = time.time() * 1000
        self.event_dispatcher.start()
        for component in self.components:
            component.start()