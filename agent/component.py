import threading
import logging
from abc import ABC, abstractmethod
from typing import Optional

from event.event import Event
from event.event_type import EventType
from event.event_dispatcher import EventDispatcher
from event.event_queue import EventQueue
from event.event_consumer import EventConsumer

class Component(EventConsumer, ABC):
    def __init__(self, event_dispatcher: EventDispatcher, agent):
        self.thread: Optional[threading.Thread] = None
        self.event_dispatcher = event_dispatcher
        self.event_queue = EventQueue()
        self.agent = agent
        self.logger = logging.getLogger(self.__class__.__name__)
        self.subscribe_events()
    
    def start(self):
        self.thread = threading.Thread(target=self.event_handling_loop)
        self.thread.daemon = True
        self.thread.name = f"{self.__class__.__name__} Event Handler"
        self.thread.start()
    
    def terminate(self):
        if self.thread:
            self.thread.join(timeout=1.0)
    
    def set_up(self):
        """Override in subclasses to initialize the component"""
        pass
    
    @abstractmethod
    def subscribe_events(self):
        """Subscribe to events that this component wants to receive"""
        pass
    
    @abstractmethod
    def handle_event(self, event: Event) -> bool:
        """
        Process an event
        
        Returns:
            bool: True if the event was handled, False if it should be put back in the queue
        """
        pass
    
    def event_handling_loop(self):
        self.set_up()
        while True:
            try:
                event = self.event_queue.get()
                if not self.handle_event(event):
                    self.event_queue.put(event)
                self.event_queue.task_done()
            except Exception as e:
                self.logger.error(f"An error occurred while handling an event: {e}", exc_info=True)
    
    def receive_event(self, event: Event):
        self.event_queue.put(event)
    
    def dispatch_event(self, event_type: EventType, event_data=None):
        class SimpleEvent(Event):
            def get_type(self):
                return event_type
            
            def get_data(self):
                return event_data
        
        self.event_dispatcher.dispatch(SimpleEvent())
    
    def subscribe_event(self, event_type: EventType):
        self.event_dispatcher.add_subscription(event_type, self)