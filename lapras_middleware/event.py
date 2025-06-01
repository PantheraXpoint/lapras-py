from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Union
import logging
import threading
from queue import Queue, Empty
import os
import json
import time
from datetime import datetime
import uuid

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
class EventMetadata:
    """Event metadata containing type and context information."""
    id: str
    timestamp: str
    type: str  # "readSensor", "updateContext", "applyAction", "actionReport"
    location: Optional[str] = None
    contextType: Optional[str] = None
    priority: str = "Normal"  # "Low", "Normal", "High", "Critical"
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

@dataclass
class EntityInfo:
    """Source or target entity information."""
    entityType: str  # "sensorAgent", "virtualAgent", "contextManager"
    entityId: str

@dataclass
class Event:
    """Unified event structure for all system communications."""
    event: EventMetadata
    source: EntityInfo
    target: EntityInfo
    payload: Dict[str, Any]

# =============================================================================
# PAYLOAD STRUCTURES FOR DIFFERENT EVENT TYPES
# =============================================================================

# ASYNCHRONOUS/CONTINUOUS EVENTS (Stream-based communication)
@dataclass
class SensorPayload:
    """Payload for readSensor events (ASYNCHRONOUS - continuous stream)."""
    sensor_type: str  # "infrared", "temperature", "humidity"
    value: Union[float, int, str, bool]
    unit: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ContextPayload:
    """Payload for updateContext events (ASYNCHRONOUS - continuous stream)."""
    agent_type: str  # "aircon", "light", "microwave"
    state: Dict[str, Any]
    sensors: Optional[Dict[str, Any]] = None

# SYNCHRONOUS/ONE-TIME EVENTS (Request-Response communication)
@dataclass
class ActionPayload:
    """Payload for applyAction events (SYNCHRONOUS - one-time request)."""
    actionName: str  # "turn_on", "turn_off", "set_temperature"
    parameters: Optional[Dict[str, Any]] = None

@dataclass
class ActionReportPayload:
    """Payload for actionReport events (SYNCHRONOUS - one-time response)."""
    command_id: str
    success: bool
    message: Optional[str] = None
    new_state: Optional[Dict[str, Any]] = None

class EventFactory:
    """Factory class to create standardized events."""
    
    # ASYNCHRONOUS EVENT CREATORS
    @staticmethod
    def create_sensor_event(
        sensor_id: str,
        virtual_agent_id: str,
        sensor_type: str,
        value: Union[float, int, str, bool],
        unit: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        location: Optional[str] = None
    ) -> Event:
        """Create a readSensor event from SensorAgent to VirtualAgent (ASYNCHRONOUS)."""
        return Event(
            event=EventMetadata(
                id="",  # Will be auto-generated
                timestamp="",  # Will be auto-generated
                type="readSensor",
                location=location,
                contextType=sensor_type
            ),
            source=EntityInfo(
                entityType="sensorAgent",
                entityId=sensor_id
            ),
            target=EntityInfo(
                entityType="virtualAgent", 
                entityId=virtual_agent_id
            ),
            payload=asdict(SensorPayload(
                sensor_type=sensor_type,
                value=value,
                unit=unit,
                metadata=metadata
            ))
        )
    
    @staticmethod
    def create_context_event(
        virtual_agent_id: str,
        agent_type: str,
        state: Dict[str, Any],
        sensors: Optional[Dict[str, Any]] = None,
        location: Optional[str] = None
    ) -> Event:
        """Create an updateContext event from VirtualAgent to ContextManager (ASYNCHRONOUS)."""
        return Event(
            event=EventMetadata(
                id="",
                timestamp="",
                type="updateContext",
                location=location,
                contextType=agent_type
            ),
            source=EntityInfo(
                entityType="virtualAgent",
                entityId=virtual_agent_id
            ),
            target=EntityInfo(
                entityType="contextManager",
                entityId="CM-MainController"
            ),
            payload=asdict(ContextPayload(
                agent_type=agent_type,
                state=state,
                sensors=sensors
            ))
        )
    
    # SYNCHRONOUS EVENT CREATORS
    @staticmethod
    def create_action_event(
        virtual_agent_id: str,
        action_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        location: Optional[str] = None,
        priority: str = "Normal"
    ) -> Event:
        """Create an applyAction event from ContextManager to VirtualAgent (SYNCHRONOUS - Request)."""
        return Event(
            event=EventMetadata(
                id="",
                timestamp="",
                type="applyAction",
                location=location,
                priority=priority
            ),
            source=EntityInfo(
                entityType="contextManager",
                entityId="CM-MainController"
            ),
            target=EntityInfo(
                entityType="virtualAgent",
                entityId=virtual_agent_id
            ),
            payload=asdict(ActionPayload(
                actionName=action_name,
                parameters=parameters
            ))
        )
    
    @staticmethod
    def create_action_report_event(
        virtual_agent_id: str,
        command_id: str,
        success: bool,
        message: Optional[str] = None,
        new_state: Optional[Dict[str, Any]] = None
    ) -> Event:
        """Create an actionReport event from VirtualAgent to ContextManager (SYNCHRONOUS - Response)."""
        return Event(
            event=EventMetadata(
                id="",
                timestamp="",
                type="actionReport"
            ),
            source=EntityInfo(
                entityType="virtualAgent",
                entityId=virtual_agent_id
            ),
            target=EntityInfo(
                entityType="contextManager",
                entityId="CM-MainController"
            ),
            payload=asdict(ActionReportPayload(
                command_id=command_id,
                success=success,
                message=message,
                new_state=new_state
            ))
        )

class MQTTMessage:
    """Utility class for MQTT message serialization/deserialization."""
    
    @staticmethod
    def serialize(event: Event) -> str:
        """Serialize Event object to JSON string for MQTT."""
        return json.dumps(asdict(event), indent=2)
    
    @staticmethod
    def deserialize(message: str) -> Event:
        """Deserialize JSON string to Event object."""
        data = json.loads(message)
        
        # Reconstruct the Event object
        event_data = data["event"]
        source_data = data["source"]
        target_data = data["target"]
        payload_data = data["payload"]
        
        return Event(
            event=EventMetadata(**event_data),
            source=EntityInfo(**source_data),
            target=EntityInfo(**target_data),
            payload=payload_data
        )
    
    @staticmethod
    def get_payload_as(event: Event, payload_class):
        """Extract payload as specific payload class."""
        if payload_class == SensorPayload:
            return SensorPayload(**event.payload)
        elif payload_class == ContextPayload:
            return ContextPayload(**event.payload)
        elif payload_class == ActionPayload:
            return ActionPayload(**event.payload)
        elif payload_class == ActionReportPayload:
            return ActionReportPayload(**event.payload)
        else:
            return event.payload

class TopicManager:
    """Manages MQTT topic naming conventions."""
    
    # ASYNCHRONOUS/CONTINUOUS TOPICS
    @staticmethod
    def sensor_broadcast(sensor_id: str) -> str:
        """Topic for readSensor events broadcasted by SensorAgent (ASYNCHRONOUS - one-to-many)."""
        return f"sensor/{sensor_id}/readSensor"
    
    @staticmethod
    def virtual_to_context(virtual_agent_id: str) -> str:
        """Topic for updateContext events from VirtualAgent to ContextManager (ASYNCHRONOUS)."""
        return f"virtual/{virtual_agent_id}/to/context/updateContext"
    
    # SYNCHRONOUS/ONE-TIME TOPICS
    @staticmethod
    def context_to_virtual_action(virtual_agent_id: str) -> str:
        """Topic for applyAction events from ContextManager to VirtualAgent (SYNCHRONOUS - Request)."""
        return f"context/to/{virtual_agent_id}/applyAction"
    
    @staticmethod
    def virtual_to_context_report(virtual_agent_id: str) -> str:
        """Topic for actionReport events from VirtualAgent to ContextManager (SYNCHRONOUS - Response)."""
        return f"virtual/{virtual_agent_id}/to/context/actionReport" 