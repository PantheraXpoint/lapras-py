from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
import logging
import threading
from queue import Queue

logger = logging.getLogger(__name__)

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
        
    def start(self) -> None:
        """Start the event dispatcher thread."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._process_events, daemon=True)
        self.thread.start()
        
    def stop(self) -> None:
        """Stop the event dispatcher thread."""
        self.running = False
        if self.thread:
            self.thread.join()
            
    def subscribe(self, component: Any, event_type: str) -> None:
        """Subscribe a component to an event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = set()
        self.subscribers[event_type].add(component)
        
    def unsubscribe(self, component: Any, event_type: str) -> None:
        """Unsubscribe a component from an event type."""
        if event_type in self.subscribers:
            self.subscribers[event_type].discard(component)
            
    def dispatch(self, event: Event) -> None:
        """Dispatch an event to all subscribed components."""
        self.event_queue.put(event)
        
    def _process_events(self) -> None:
        """Process events from the queue."""
        while self.running:
            try:
                event = self.event_queue.get(timeout=1.0)
                self._handle_event(event)
            except Queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
                
    def _handle_event(self, event: Event) -> None:
        """Handle a single event by dispatching it to subscribers."""
        if event.type not in self.subscribers:
            return
            
        for component in self.subscribers[event.type]:
            try:
                component.handle_event(event)
            except Exception as e:
                logger.error(f"Error handling event in component {component}: {e}", exc_info=True) 