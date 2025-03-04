from abc import ABC, abstractmethod
from event.event_type import EventType

class Event(ABC):
    @abstractmethod
    def get_type(self) -> EventType:
        pass
    
    @abstractmethod
    def get_data(self):
        pass
