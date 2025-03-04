import logging
import threading
import time
from typing import Dict, List, Set, Optional, Any
from threading import Timer

from agent.component import Component
from event.event import Event
from event.event_type import EventType
from event.event_dispatcher import EventDispatcher
from communicator.lapras_topic import LaprasTopic
from communicator.message_type import MessageType
from communicator.mqtt_topic import MqttTopic
from context.context_instance import ContextInstance

class ContextManager(Component):
    def __init__(self, event_dispatcher: EventDispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.logger = logging.getLogger(__name__)
        
        self.mqtt_communicator = agent.get_mqtt_communicator()
        self.context_map: Dict[str, ContextInstance] = {}
        self.contexts_published_as_updated: Set[str] = set()
        self.periodic_timers: Dict[str, Timer] = {}
    
    def subscribe_events(self):
        self.subscribe_event(EventType.MESSAGE_ARRIVED)
    
    def handle_event(self, event: Event) -> bool:
        if event.get_type() == EventType.MESSAGE_ARRIVED:
            data = event.get_data()
            topic = data[0]
            payload = data[1]
            
            if topic.get_message_type() != MessageType.CONTEXT:
                return True
            
            context_instance = ContextInstance.from_payload(payload)
            if not context_instance:
                return True
                
            self.logger.debug(
                f"Context message arrived (name={context_instance.get_name()}, "
                f"value={context_instance.get_value()}, "
                f"timestamp={context_instance.get_timestamp()}, "
                f"publisher={context_instance.get_publisher()})"
            )
            
            self.update_context_internal(context_instance)
            return True
            
        return True
    
    def publish_context(self, context_name: str, refresh_timestamp: bool = False):
        context_instance = self.context_map.get(context_name)
        if not context_instance:
            return
            
        if refresh_timestamp:
            context_instance.set_timestamp(int(time.time() * 1000))
            
        self.logger.info(f"Publishing context {context_name} = {context_instance.get_value()}")
        topic = LaprasTopic(None, MessageType.CONTEXT, context_name)
        self.mqtt_communicator.publish(topic, context_instance)
    
    def subscribe_context(self, context_name: Optional[str] = None):
        if context_name is None:
            self.logger.info("Subscribing to all contexts")
            topic = LaprasTopic(None, MessageType.CONTEXT, MqttTopic.SINGLELEVEL_WILDCARD)
        else:
            self.logger.info(f"Subscribing to context {context_name}")
            topic = LaprasTopic(None, MessageType.CONTEXT, context_name)
            
        self.mqtt_communicator.subscribe_topic(topic)
    
    def update_context(self, context_name: str, context_value: Any, publisher: str, timestamp: Optional[int] = None):
        if timestamp is None:
            timestamp = int(time.time() * 1000)
            
        context_instance = ContextInstance(context_name, context_value, timestamp, publisher)
        self.update_context_internal(context_instance)
    
    def update_context_internal(self, context_instance: ContextInstance):
        context_name = context_instance.get_name()
        former_context_instance = self.context_map.get(context_name)
        
        if (not former_context_instance or 
            former_context_instance.get_timestamp() < context_instance.get_timestamp()):
            
            self.logger.info(f"Updating context {context_name} to {context_instance.get_value()}")
            self.context_map[context_name] = context_instance
            self.dispatch_event(EventType.CONTEXT_UPDATED, context_instance)
            
            if context_name in self.contexts_published_as_updated:
                self.publish_context(context_name)
    
    def set_publish_as_updated(self, context_name: str):
        self.logger.info(f"Publish-as-updated set for context {context_name}")
        self.contexts_published_as_updated.add(context_name)
    
    def set_periodic_publish(self, context_name: str, interval: int):
        self.logger.info(f"Periodic publish set for context {context_name} every {interval} seconds")
        
        # Cancel existing timer if there is one
        if context_name in self.periodic_timers:
            self.periodic_timers[context_name].cancel()
        
        # Function that publishes and reschedules itself
        def publish_and_reschedule():
            self.publish_context(context_name, True)
            self.periodic_timers[context_name] = Timer(interval, publish_and_reschedule)
            self.periodic_timers[context_name].daemon = True
            self.periodic_timers[context_name].start()
            
        # Start the initial timer
        self.periodic_timers[context_name] = Timer(interval, publish_and_reschedule)
        self.periodic_timers[context_name].daemon = True
        self.periodic_timers[context_name].start()
    
    def get_context(self, context_name: str) -> Optional[ContextInstance]:
        return self.context_map.get(context_name)
    
    def list_contexts(self) -> List[ContextInstance]:
        return list(self.context_map.values())