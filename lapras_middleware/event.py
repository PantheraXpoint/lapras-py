from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
import logging
import threading
from queue import Queue, Empty
import os
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Create a dedicated logger for events
event_logger = logging.getLogger('event_logger')
event_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Create file handler for events
event_file_handler = logging.FileHandler('logs/events.log')
event_file_handler.setLevel(logging.INFO)

# Create formatter for event logs
event_formatter = logging.Formatter('%(asctime)s - %(message)s')
event_file_handler.setFormatter(event_formatter)

# Add handler to event logger
event_logger.addHandler(event_file_handler)

@dataclass
class Event:
    """Represents an event in the system."""
    type: str
    data: Any
    timestamp: Optional[int] = None

class EventDispatcher:
    """Handles event dispatching to subscribed components."""
    
    def __init__(self):
        """Initialize the event dispatcher."""
        self.subscribers: Dict[str, Set[Any]] = {}
        self.event_queue: Queue = Queue()
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()  # Lock for thread-safe operations
        
    def start(self) -> None:
        """Start the event dispatcher thread."""
        with self._lock:
            if self.running:
                logger.warning("Event dispatcher is already running")
                return
                
            self.running = True
            self.thread = threading.Thread(target=self._process_events, daemon=True)
            self.thread.start()
            logger.info("[EVENT_DISPATCHER] Event dispatcher started")
            logger.info(f"[EVENT_DISPATCHER] Current subscribers: {json.dumps({k: [c.__class__.__name__ for c in v] for k, v in self.subscribers.items()}, indent=2)}")
            event_logger.info("=== Event Dispatcher Started ===")
        
    def stop(self) -> None:
        """Stop the event dispatcher thread."""
        with self._lock:
            if not self.running:
                logger.warning("Event dispatcher is not running")
                return
                
            self.running = False
            if self.thread:
                self.thread.join(timeout=5.0)  # Wait up to 5 seconds for thread to finish
            logger.info("[EVENT_DISPATCHER] Event dispatcher stopped")
            event_logger.info("=== Event Dispatcher Stopped ===")
            
    def subscribe(self, component: Any, event_type: str) -> None:
        """Subscribe a component to an event type."""
        with self._lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = set()
            self.subscribers[event_type].add(component)
            logger.info(f"[EVENT_DISPATCHER] Component {component.__class__.__name__} subscribed to event: {event_type}")
            logger.info(f"[EVENT_DISPATCHER] Current subscribers for {event_type}: {[c.__class__.__name__ for c in self.subscribers[event_type]]}")
            event_logger.info(f"SUBSCRIBE: {component.__class__.__name__} -> {event_type}")
        
    def unsubscribe(self, component: Any, event_type: str) -> None:
        """Unsubscribe a component from an event type."""
        with self._lock:
            if event_type in self.subscribers:
                self.subscribers[event_type].discard(component)
                logger.info(f"Component {component.__class__.__name__} unsubscribed from event: {event_type}")
                event_logger.info(f"UNSUBSCRIBE: {component.__class__.__name__} -> {event_type}")
            
    def dispatch(self, event: Event) -> None:
        """Dispatch an event to all subscribed components."""
        if not self.running:
            logger.warning("[EVENT_DISPATCHER] Event dispatcher is not running, event not dispatched")
            return
            
        logger.info(f"[EVENT_DISPATCHER] Dispatching event: {event.type}")
        logger.info(f"[EVENT_DISPATCHER] Event data: {json.dumps(event.data, indent=2) if isinstance(event.data, (dict, list)) else event.data}")
        logger.info(f"[EVENT_DISPATCHER] Subscribers for {event.type}: {[c.__class__.__name__ for c in self.subscribers.get(event.type, set())]}")
        event_logger.info(f"DISPATCH: {event.type} - Data: {event.data}")
        self.event_queue.put(event)
        
    def _process_events(self) -> None:
        """Process events from the queue."""
        logger.info("[EVENT_DISPATCHER] Event processing thread started")
        while self.running:
            try:
                event = self.event_queue.get(timeout=1.0)
                logger.info(f"[EVENT_DISPATCHER] Processing event: {event.type}")
                self._handle_event(event)
                self.event_queue.task_done()
                logger.info(f"[EVENT_DISPATCHER] Event processed: {event.type}")
            except Empty:
                continue
            except Exception as e:
                logger.error(f"[EVENT_DISPATCHER] Error processing event: {e}", exc_info=True)
                event_logger.error(f"ERROR: {str(e)}")
                
    def _handle_event(self, event: Event) -> None:
        """Handle a single event by dispatching it to subscribers."""
        with self._lock:
            if event.type not in self.subscribers:
                logger.debug(f"[EVENT_DISPATCHER] No subscribers for event: {event.type}")
                event_logger.info(f"NO_SUBSCRIBERS: {event.type}")
                return
                
            subscribers = self.subscribers[event.type].copy()  # Create a copy to avoid modification during iteration
            logger.info(f"[EVENT_DISPATCHER] Found {len(subscribers)} subscribers for event: {event.type}")
            
        for component in subscribers:
            try:
                logger.info(f"[EVENT_DISPATCHER] Component {component.__class__.__name__} handling event: {event.type}")
                event_logger.info(f"HANDLE: {component.__class__.__name__} -> {event.type}")
                component.handle_event(event)
                logger.info(f"[EVENT_DISPATCHER] Component {component.__class__.__name__} handled event: {event.type}")
            except Exception as e:
                logger.error(f"[EVENT_DISPATCHER] Error handling event in component {component.__class__.__name__}: {e}", exc_info=True)
                event_logger.error(f"ERROR: {component.__class__.__name__} -> {event.type} - {str(e)}") 