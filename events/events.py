from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Set, Protocol
import threading
import queue
import logging

logger = logging.getLogger(__name__)

class EventType(Enum):
    MESSAGE_ARRIVED = auto()
    CONTEXT_UPDATED = auto()
    ACTION_TAKEN = auto()
    TASK_NOTIFIED = auto()
    USER_NOTIFIED = auto()
    SUBSCRIBE_TOPIC_REQUESTED = auto()
    PUBLISH_MESSAGE_REQUESTED = auto()

class Event(Protocol):
    """Protocol defining what an event should look like."""
    @property
    def type(self) -> EventType:
        """Get the event type."""
        ...
    
    @property
    def data(self) -> Any:
        """Get the event data."""
        ...

@dataclass
class BasicEvent:
    """Basic implementation of the Event protocol."""
    type: EventType
    data: Any = None

class EventConsumer(ABC):
    """Abstract base class for event consumers."""
    @abstractmethod
    def receive_event(self, event: Event) -> None:
        """Handle received event."""
        pass

class EventDispatcher:
    def __init__(self):
        self._consumers: Dict[EventType, Set[EventConsumer]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    def start(self):
        """Start the event dispatcher thread."""
        with self._lock:
            if not self._running:
                self._running = True
                self._thread = threading.Thread(target=self._dispatch_loop)
                self._thread.daemon = True
                self._thread.start()

    def subscribe(self, event_type: EventType, consumer: 'EventConsumer'):
        """Subscribe a consumer to an event type."""
        with self._lock:
            if event_type not in self._consumers:
                self._consumers[event_type] = set()
            self._consumers[event_type].add(consumer)

    def dispatch(self, event: Event):
        """Dispatch an event to all subscribed consumers."""
        with self._lock:
            if event.type in self._consumers:
                for consumer in self._consumers[event.type]:
                    try:
                        consumer.receive_event(event)
                    except Exception as e:
                        logger.error(f"Error dispatching event: {e}")

class EventQueue:
    """Thread-safe event queue implementation."""
    def __init__(self):
        self._queue = queue.Queue()

    def put(self, event: 'Event') -> None:
        """Put an event into the queue."""
        self._queue.put(event)

    def take(self) -> 'Event':
        """Take an event from the queue (blocking)."""
        return self._queue.get()

    def add(self, event: 'Event') -> None:
        """Add an event to the queue (alias for put)."""
        self.put(event)