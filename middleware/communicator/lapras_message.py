import json
import time
from typing import ClassVar, Type, Optional, TypeVar
from communicator.mqtt_message import MqttMessage

T = TypeVar('T', bound='LaprasMessage')

class LaprasMessage(MqttMessage):
    def __init__(self, name: Optional[str] = None, timestamp: Optional[int] = None, publisher: Optional[str] = None):
        self.name = name
        self.timestamp = timestamp or int(time.time() * 1000)
        self.publisher = publisher
    
    @classmethod
    def from_payload(cls: Type[T], payload: bytes) -> Optional[T]:
        json_obj = MqttMessage.from_payload(payload, cls)
        if json_obj:
            instance = cls()
            for key, value in json_obj.items():
                setattr(instance, key, value)
            return instance
        return None
    
    def get_name(self) -> str:
        return self.name
    
    def set_name(self, name: str):
        self.name = name
    
    def get_publisher(self) -> str:
        return self.publisher
    
    def set_publisher(self, publisher: str):
        self.publisher = publisher
    
    def get_timestamp(self) -> int:
        return self.timestamp
    
    def set_timestamp(self, timestamp: int):
        self.timestamp = timestamp