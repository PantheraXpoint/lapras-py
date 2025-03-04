import threading
import logging
from typing import Dict, Set
from event.event import Event
from event.event_type import EventType
from event.event_consumer import EventConsumer
from event.event_queue import EventQueue

class EventDispatcher:
    def __init__(self):
        self.event_queue = EventQueue()
        self.consumer_map: Dict[EventType, Set[EventConsumer]] = {}
        self.thread = None
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.name = self.__class__.__name__
        self.thread.start()
    
    def add_subscription(self, event_type: EventType, consumer: EventConsumer):
        if event_type not in self.consumer_map:
            self.consumer_map[event_type] = set()
        self.consumer_map[event_type].add(consumer)
    
    def dispatch(self, event: Event):
        self.event_queue.put(event)
    
    def run(self):
        while True:
            try:
                event = self.event_queue.get()
                consumers = self.consumer_map.get(event.get_type())
                if consumers:
                    for consumer in consumers:
                        consumer.receive_event(event)
                self.event_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")