from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Type
from datetime import datetime
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import threading
import time

from .component import Component
from .event import Event, EventDispatcher
# from .agent import Agent
from .communicator import MqttCommunicator, MqttMessage

logger = logging.getLogger(__name__)

def context_field(name: str = "", publish_as_updated: bool = False, publish_interval: int = 0):
    """Decorator for context fields."""
    def decorator(field):
        field.context_field = {
            'name': name or field.__name__,
            'publish_as_updated': publish_as_updated,
            'publish_interval': publish_interval
        }
        return field
    return decorator

@dataclass
class ContextInstance:
    """Represents a context instance in the system."""
    name: str
    value: Any
    timestamp: int
    publisher: str
    value_type: Optional[str] = None
    
    def __post_init__(self):
        """Initialize value type after initialization."""
        if self.value_type is None and self.value is not None:
            self.value_type = type(self.value).__name__
    
    @classmethod
    def from_payload(cls, payload: bytes) -> Optional['ContextInstance']:
        """Create a ContextInstance from a payload."""
        try:
            data = json.loads(payload.decode('utf-8'))
            value = data['value']
            value_type = data.get('value_type')
            
            # Try to convert value to the specified type
            if value_type:
                try:
                    type_class = eval(value_type)  # Convert string to type
                    value = type_class(value)
                except (NameError, ValueError):
                    pass  # Keep value as is if conversion fails
            
            return cls(
                name=data['name'],
                value=value,
                timestamp=data['timestamp'],
                publisher=data['publisher'],
                value_type=value_type
            )
        except Exception as e:
            logger.error(f"Failed to parse context payload: {e}", exc_info=True)
            return None
    
    def to_payload(self) -> bytes:
        """Convert the instance to a payload."""
        data = {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp,
            'publisher': self.publisher,
            'value_type': self.value_type
        }
        return json.dumps(data).encode('utf-8')
    
    @property
    def message_type(self) -> str:
        """Get the message type."""
        return "CONTEXT"
    
    @property
    def qos(self) -> int:
        """Get the QoS level."""
        return 1  # AT_LEAST_ONCE
    
    @property
    def retained(self) -> bool:
        """Get whether the message should be retained."""
        return True

class ContextManager(Component):
    """Manages context information in the system."""
    
    def __init__(self, event_dispatcher, agent):
        """Initialize the context manager."""
        super().__init__(event_dispatcher, agent)
        
        self.mqtt_communicator = agent.mqtt_communicator
        self.context_map: Dict[str, ContextInstance] = {}
        self.contexts_published_as_updated: Set[str] = set()
        self.lock = Lock()
        
        # Initialize periodic publisher
        self.periodic_publisher = ThreadPoolExecutor(max_workers=1)
        self.publish_tasks: Dict[str, threading.Timer] = {}
        
    def _handle_context_message(self, topic: str, payload: bytes) -> None:
        """Handle incoming context messages."""
        self.event_dispatcher.dispatch(Event(
            type="MESSAGE_ARRIVED",
            data=(topic, payload),
            timestamp=int(time.time() * 1000)
        ))
        
    def start(self) -> None:
        """Start the context manager."""
        # Subscribe to context topics
        self.mqtt_communicator.subscribe(
            "context/#",
            self._handle_context_message
        )
        
        # Subscribe to events
        self.event_dispatcher.subscribe(self, "MESSAGE_ARRIVED")
        
    def handle_event(self, event: Event) -> bool:
        """Handle events."""
        if event.type == "MESSAGE_ARRIVED":
            topic, payload = event.data
            if not topic.startswith("context/"):
                return True
                
            context_instance = ContextInstance.from_payload(payload)
            if context_instance:
                logger.debug(
                    "Context message arrived (name=%s, value=%s, timestamp=%d, publisher=%s)",
                    context_instance.name,
                    context_instance.value,
                    context_instance.timestamp,
                    context_instance.publisher
                )
                self.update_context(context_instance)
            return True
            
        return False
    
    def publish_context(self, context_name: str, refresh_timestamp: bool = False) -> None:
        """Publish a context to the MQTT broker."""
        context_instance = self.context_map.get(context_name)
        if context_instance is None:
            return
            
        if refresh_timestamp:
            context_instance.timestamp = int(time.time() * 1000)
            
        logger.info("Publishing context %s = %s", context_name, context_instance.value)
        
        self.mqtt_communicator.publish(MqttMessage(
            topic=f"context/{context_name}",
            payload=context_instance.to_payload(),
            qos=context_instance.qos,
            retain=context_instance.retained
        ))
    
    def subscribe_context(self, context_name: Optional[str] = None) -> None:
        """Subscribe to context updates."""
        if context_name is None:
            logger.info("Subscribing to all contexts")
            self.mqtt_communicator.subscribe("context/#", self._handle_context_message)
        else:
            logger.info("Subscribing to context %s", context_name)
            self.mqtt_communicator.subscribe(f"context/{context_name}", self._handle_context_message)
    
    def update_context(self, context_name: str, context_value: Any, publisher: str, timestamp: Optional[int] = None) -> None:
        """Update a context with new values."""
        if timestamp is None:
            timestamp = int(time.time() * 1000)
            
        context_instance = ContextInstance(
            name=context_name,
            value=context_value,
            timestamp=timestamp,
            publisher=publisher
        )
        self.update_context_instance(context_instance)
    
    def update_context_instance(self, context_instance: ContextInstance) -> None:
        """Update a context with a new instance."""
        with self.lock:
            former_instance = self.context_map.get(context_instance.name)
            if (former_instance is None or 
                former_instance.timestamp < context_instance.timestamp):
                logger.info(
                    "Updating context %s to %s",
                    context_instance.name,
                    context_instance.value
                )
                self.context_map[context_instance.name] = context_instance
                
                self.event_dispatcher.dispatch(Event(
                    type="CONTEXT_UPDATED",
                    data=context_instance,
                    timestamp=context_instance.timestamp
                ))
                
                if context_instance.name in self.contexts_published_as_updated:
                    self.publish_context(context_instance.name)
    
    def set_publish_as_updated(self, context_name: str) -> None:
        """Set a context to be published when updated."""
        logger.info("Publish-as-updated set for context %s", context_name)
        self.contexts_published_as_updated.add(context_name)
    
    def set_periodic_publish(self, context_name: str, interval: int) -> None:
        """Set a context to be published periodically."""
        logger.info("Periodic publish set for context %s every %d seconds", context_name, interval)
        
        def publish_task():
            self.publish_context(context_name, True)
            # Schedule next publish
            self.publish_tasks[context_name] = threading.Timer(interval, publish_task)
            self.publish_tasks[context_name].start()
        
        # Start periodic publishing
        self.publish_tasks[context_name] = threading.Timer(0, publish_task)
        self.publish_tasks[context_name].start()
    
    def get_context(self, context_name: str) -> Optional[ContextInstance]:
        """Get a context instance by name."""
        return self.context_map.get(context_name)
    
    def list_contexts(self) -> List[ContextInstance]:
        """Get all context instances."""
        return list(self.context_map.values())
    
    def stop(self) -> None:
        """Stop the context manager."""
        # Cancel all periodic publish tasks
        for timer in self.publish_tasks.values():
            timer.cancel()
        self.publish_tasks.clear()
        
        # Shutdown periodic publisher
        self.periodic_publisher.shutdown(wait=True) 