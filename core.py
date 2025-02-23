from abc import ABC, abstractmethod
import logging
import threading
from typing import Optional, TYPE_CHECKING

from .events.events import EventConsumer
from .events.events import Event
from .events.events import EventType
from .events.events import EventQueue

if TYPE_CHECKING:
    from .events.events import EventDispatcher
    from agent import Agent

logger = logging.getLogger(__name__)

class Component(EventConsumer, ABC):
    def __init__(self, event_dispatcher: 'EventDispatcher', agent: 'Agent'):
        self._thread: Optional[threading.Thread] = None
        self._event_dispatcher = event_dispatcher
        self._event_queue = EventQueue()
        self._agent = agent
        self.subscribe_events()

    def start(self):
        self._thread = threading.Thread(target=self._event_handling_loop)
        self._thread.name = f"{self.__class__.__name__} Event Handler"
        self._thread.daemon = True
        self._thread.start()

    def terminate(self):
        if self._thread:
            self._thread.interrupt()
            try:
                self._thread.join()
            except InterruptedError:
                pass

    def set_up(self):
        """Set up the component. Override if needed."""
        pass

    @abstractmethod
    def subscribe_events(self):
        """Subscribe to relevant event types."""
        pass

    @abstractmethod
    def handle_event(self, event: Event) -> bool:
        """Handle an event. Return True if handled, False to requeue."""
        pass

    def _event_handling_loop(self):
        self.set_up()
        while True:
            try:
                event = self._event_queue.take()
                if not self.handle_event(event):
                    self._event_queue.put(event)
            except InterruptedError:
                break
            except Exception as e:
                logger.error("An error occurred while handling an event", exc_info=e)

    def receive_event(self, event: Event):
        self._event_queue.add(event)

    def subscribe_event(self, event_type: EventType):
        self._event_dispatcher.subscribe(event_type, self)