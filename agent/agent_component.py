# lapras/agent/agent_component.py
import logging
import threading
import inspect
from typing import Dict, Optional, Any, Type, Set
import time

from agent.component import Component
from context.context import Context
from context.context_field import ContextField
from communicator.mqtt_communicator import MqttCommunicator
from communicator.lapras_topic import LaprasTopic
from communicator.message_type import MessageType
from context.context_instance import ContextInstance
from context.context_manager import ContextManager
from functionality.functionality_executor import FunctionalityExecutor
from event.event import Event
from event.event_type import EventType
from event.event_dispatcher import EventDispatcher

# Import these if you've already implemented them
# from action.action_manager import ActionManager
# from task.task_manager import TaskManager
# from user.user_manager import UserManager

class FunctionalityMethod:
    """
    A decorator to mark methods as functionality methods.
    In Java, this was an annotation.
    """
    def __init__(self, name="", description=""):
        self.name = name
        self.description = description
        self.func = None
    
    def __call__(self, func):
        self.func = func
        func._functionality_method = self
        return func
    
    @staticmethod
    def get_functionality_name(method):
        """Get the functionality name for a method"""
        if hasattr(method, '_functionality_method'):
            fm = method._functionality_method
            if fm.name:
                return fm.name
        return method.__name__.capitalize()

class AgentComponent(Component):
    """Base class for agent components"""
    
    OPERATING_STATUS_SUFFIX = "OperatingStatus"
    OPERATING_STATUS_INTERVAL = 300  # seconds
    
    def __init__(self, event_dispatcher: EventDispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.agent_config = agent.get_agent_config()
        self.agent_name = self.agent_config.get_agent_name()
        self.mqtt_communicator = agent.get_mqtt_communicator()
        self.context_manager = agent.get_context_manager()
        self.functionality_executor = agent.get_functionality_executor()
        
        # These would be initialized if you've implemented them
        self.action_manager = getattr(agent, 'get_action_manager', lambda: None)()
        self.task_manager = getattr(agent, 'get_task_manager', lambda: None)()
        self.user_manager = getattr(agent, 'get_user_manager', lambda: None)()
        
        # Process annotations (in Python, we use descriptors and reflection)
        self.context_field_map = {}
        self.context_map = {}
        
        self._process_annotations()
        
        # Subscribe to contexts specified in config
        for context_name in self.agent_config.get_option_as_array('subscribe_contexts'):
            self.context_manager.subscribe_context(context_name)
        
        # Set up operating status
        self.operating_status_name = f"{self.agent_name}{self.OPERATING_STATUS_SUFFIX}"
        context_instance = ContextInstance(
            self.operating_status_name, 
            "Dead", 
            int(time.time() * 1000), 
            self.agent_name
        )
        
        topic = LaprasTopic(None, MessageType.CONTEXT, self.operating_status_name)
        self.mqtt_communicator.set_will(topic, context_instance.get_payload(), 2, True)
        
        # Thread for agent component
        self.agent_thread = None
    
    def _process_annotations(self):
        """Process annotations (in Python, using inspection)"""
        # Process context fields
        for name, attr in inspect.getmembers(self.__class__):
            if isinstance(attr, ContextField):
                context_name = attr.name or name.capitalize()
                
                # Register context
                if hasattr(self, name) and isinstance(getattr(self, name), Context):
                    context = getattr(self, name)
                    context.set_name(context_name)
                    self.context_map[context_name] = context
                else:
                    # Legacy approach
                    self.context_field_map[context_name] = name
                
                self.context_manager.subscribe_context(context_name)
                
                if attr.publish_interval > 0:
                    self.context_manager.set_periodic_publish(context_name, attr.publish_interval)
                
                if attr.publish_as_updated:
                    self.context_manager.set_publish_as_updated(context_name)
        
        if self.context_field_map:
            self.subscribe_event(EventType.CONTEXT_UPDATED)
        
        # Process functionality methods
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, '_functionality_method'):
                functionality_name = FunctionalityMethod.get_functionality_name(method)
                self.functionality_executor.register_method_functionality(functionality_name, method.__func__, self)
    
    def set_up(self):
        """Set up the agent component"""
        self.context_manager.update_context(self.operating_status_name, "Alive", self.agent_name)
        self.context_manager.set_periodic_publish(self.operating_status_name, self.OPERATING_STATUS_INTERVAL)
        
        # Subscribe to all contexts in context_field_map
        for context_name in self.context_field_map:
            self.context_manager.subscribe_context(context_name)
    
    def start(self):
        """Start the agent component"""
        super().start()
        
        self.agent_thread = threading.Thread(target=self.run)
        self.agent_thread.name = self.__class__.__name__
        self.agent_thread.daemon = True
        self.agent_thread.start()
    
    def subscribe_events(self):
        """Subscribe to events"""
        self.subscribe_event(EventType.CONTEXT_UPDATED)
    
    def handle_event(self, event: Event) -> bool:
        """Handle events"""
        if event.get_type() == EventType.CONTEXT_UPDATED:
            context_instance = event.get_data()
            context = self.context_map.get(context_instance.get_name())
            field_name = self.context_field_map.get(context_instance.get_name())
            
            if context is None and field_name is None:
                return True
            
            if context is not None:
                self.logger.debug(f"Updating context instance {context.get_name()}")
                context.set_instance(context_instance)
            else:
                self.logger.debug(f"Setting context field {field_name} to {context_instance.get_value()}")
                try:
                    self.set_context_field(field_name, context_instance.get_value())
                except AttributeError:
                    pass
            
            return True
        
        return False
    
    def set_context_field(self, field_name: str, value: Any):
        """Set a context field"""
        if hasattr(self, field_name):
            setattr(self, field_name, value)
    
    def run(self):
        """
        Main agent component thread.
        This method should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement run()")