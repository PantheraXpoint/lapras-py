import json
import inspect
import time
from typing import Any, Optional, Dict, Type

from communicator.lapras_message import LaprasMessage
from communicator.message_type import MessageType
from communicator.message_qos import MessageQos
from communicator.mqtt_message import MqttMessage

class ContextInstance(LaprasMessage):
    def __init__(self, name: Optional[str] = None, value=None, timestamp: Optional[int] = None, publisher: Optional[str] = None):
        super().__init__(name, timestamp, publisher)
        if value is not None:
            self.set_value(value)
    
    @classmethod
    def from_payload(cls, payload: bytes) -> Optional['ContextInstance']:
        json_obj = MqttMessage.from_payload(payload, cls)
        if json_obj:
            try:
                # Handle the value type conversion
                value = json_obj.get('value')
                value_type = json_obj.get('value_type')
                
                if value_type:
                    # Try to convert the value to the specified type
                    try:
                        # For basic types
                        if value_type == 'str':
                            value = str(value)
                        elif value_type == 'int':
                            value = int(value)
                        elif value_type == 'float':
                            value = float(value)
                        elif value_type == 'bool':
                            value = bool(value)
                        # For more complex types, you might need additional logic
                    except (ValueError, TypeError):
                        # If conversion fails, keep as is
                        pass
                
                return cls(
                    name=json_obj.get('name'),
                    value=value,
                    timestamp=json_obj.get('timestamp'),
                    publisher=json_obj.get('publisher')
                )
            except Exception as e:
                print(f"Error parsing context instance: {e}")
                return None
        return None
    
    def get_value(self):
        return self.value
    
    def set_value(self, value):
        self.value = value
        self.value_type = type(value).__name__
    
    def get_value_type(self) -> Type:
        if hasattr(self, 'value_type') and self.value_type:
            try:
                return eval(self.value_type)
            except (NameError, SyntaxError):
                return str
        return str
    
    def get_type(self) -> MessageType:
        return MessageType.CONTEXT
    
    def get_qos(self) -> MessageQos:
        return MessageQos.AT_LEAST_ONCE
    
    def get_retained(self) -> bool:
        return True