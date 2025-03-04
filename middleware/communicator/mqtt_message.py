from abc import ABC, abstractmethod
import json
from typing import ClassVar, Type, Any, Optional
from communicator.message_type import MessageType
from communicator.message_qos import MessageQos

class MqttMessage(ABC):
    @abstractmethod
    def get_type(self) -> MessageType:
        pass
    
    @abstractmethod
    def get_qos(self) -> MessageQos:
        pass
    
    @abstractmethod
    def get_retained(self) -> bool:
        pass
    
    def get_payload(self) -> bytes:
        return json.dumps(self.__dict__).encode('utf-8')
    
    @staticmethod
    def from_payload(payload: bytes, cls: Type['MqttMessage']) -> Optional[dict]:
        try:
            return json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError:
            return None
