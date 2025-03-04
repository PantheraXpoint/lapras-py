from abc import ABC, abstractmethod
from event.event import Event

class EventConsumer(ABC):
    @abstractmethod
    def receive_event(self, event: Event):
        pass