from abc import ABC, abstractmethod
from typing import Dict, Optional, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor
import time

from ..core import Component
from ..events.events import Event, EventType

if TYPE_CHECKING:
    from ..agent import Agent
    from ..events.events import EventDispatcher
    from .communicator.mqtt import MqttCommunicator
    from .context.context import Context,ContextManager
    from functionality.functionality import FunctionalityExecutor

class AgentComponent(Component, ABC):
    """Base class for agent components."""
    # ... rest of implementation
    
    OPERATING_STATUS_SUFFIX = "OperatingStatus"
    OPERATING_STATUS_INTERVAL = 300

    def __init__(self, event_dispatcher: 'EventDispatcher', agent: 'Agent'):
        super().__init__(event_dispatcher, agent)
        self.agent_name = agent.agent_config.agent_name
        self.operating_status_name = f"{self.agent_name}{self.OPERATING_STATUS_SUFFIX}"
        
        # Get references to managers
        self.mqtt_communicator = agent.mqtt_communicator
        self.context_manager = agent.context_manager
        self.functionality_executor = agent.functionality_executor

        # Initialize maps
        self.context_field_map: Dict[str, str] = {}
        self.context_map: Dict[str, 'Context'] = {}

        # Process annotations and subscribe contexts
        self._process_annotations()
        for context_name in agent.agent_config.get_option_as_array("subscribe_contexts"):
            self.context_manager.subscribe_context(context_name)

        # Set up operating status
        self._setup_operating_status()

    @abstractmethod
    def run(self) -> None:
        """Main run loop for the agent component."""
        pass

    def _process_annotations(self) -> None:
        """Process class annotations for context fields."""
        # Implementation will depend on how you want to handle Java annotations
        pass

    def _setup_operating_status(self) -> None:
        """Set up the operating status monitoring."""
        from .context.context import ContextInstance
        from .communicator.topic import LaprasTopic, MessageType

        context_instance = ContextInstance(
            self.operating_status_name,
            "Dead",
            int(time.time() * 1000),
            self.agent_name
        )
        topic = LaprasTopic(None, MessageType.CONTEXT, self.operating_status_name)
        self.mqtt_communicator.set_will(topic, context_instance.payload, 2, True)