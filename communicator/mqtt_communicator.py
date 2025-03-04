import threading
import logging
from typing import List, Optional, Tuple

import paho.mqtt.client as mqtt
from agent.component import Component
from event.event import Event
from event.event_type import EventType
from event.event_dispatcher import EventDispatcher
from communicator.lapras_topic import LaprasTopic
from communicator.mqtt_message import MqttMessage

class MqttCommunicator(Component):
    def __init__(self, event_dispatcher: EventDispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.logger = logging.getLogger(__name__)
        
        self.place_name = agent.get_agent_config().get_place_name()
        self.broker_address = agent.get_agent_config().get_broker_address()
        self.client_id = f"lapras-{agent.get_agent_config().get_agent_name()}-{id(self)}"
        
        # MQTT client setup
        self.mqtt_client = mqtt.Client(client_id=self.client_id)
        self.mqtt_client.on_message = self.message_arrived
        self.mqtt_client.on_connect = self.on_connect
        
        # Connection options
        self.mqtt_client.clean_session = True
        
        self.subscription_list = []
    
    def set_up(self):
        try:
            self.connect()
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
    
    def subscribe_events(self):
        self.subscribe_event(EventType.SUBSCRIBE_TOPIC_REQUESTED)
        self.subscribe_event(EventType.PUBLISH_MESSAGE_REQUESTED)
    
    def handle_event(self, event: Event) -> bool:
        try:
            if not self.mqtt_client.is_connected():
                self.connect()
                
            if event.get_type() == EventType.SUBSCRIBE_TOPIC_REQUESTED:
                topic = event.get_data()
                topic.set_place_name(self.place_name)
                self.logger.info(f"Subscribing to {topic}")
                self.subscription_list.append(topic)
                self.mqtt_client.subscribe(str(topic))
                return True
                
            elif event.get_type() == EventType.PUBLISH_MESSAGE_REQUESTED:
                data = event.get_data()
                topic = data[0]
                message = data[1]
                topic.set_place_name(self.place_name)
                self.logger.info(f"Publishing to {topic}")
                self.mqtt_client.publish(
                    str(topic), 
                    message.get_payload(), 
                    qos=message.get_qos().value, 
                    retain=message.get_retained()
                )
                return True
                
            return False
        except Exception as e:
            self.logger.error(f"Error handling event: {e}")
            return False
    
    def message_arrived(self, client, userdata, msg):
        try:
            lapras_topic = LaprasTopic.from_string(msg.topic)
            self.dispatch_event(EventType.MESSAGE_ARRIVED, [lapras_topic, msg.payload])
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            # Resubscribe to all topics
            for topic in self.subscription_list:
                self.mqtt_client.subscribe(str(topic))
        else:
            self.logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
    
    def get_subscription_list(self) -> List[LaprasTopic]:
        return self.subscription_list[:]
    
    def subscribe_topic(self, topic: LaprasTopic):
        self.dispatch_event(EventType.SUBSCRIBE_TOPIC_REQUESTED, topic)
    
    def publish(self, topic: LaprasTopic, message: MqttMessage):
        self.dispatch_event(EventType.PUBLISH_MESSAGE_REQUESTED, [topic, message])
    
    def set_will(self, topic: LaprasTopic, payload: bytes, qos: int, retained: bool):
        topic.set_place_name(self.place_name)
        self.mqtt_client.will_set(str(topic), payload, qos, retained)
    
    def connect(self):
        try:
            self.logger.debug(f"Connecting to MQTT broker at {self.broker_address}")
            self.mqtt_client.connect(self.broker_address)
            self.mqtt_client.loop_start()  # Start the background thread
            self.logger.info("Connected to MQTT broker")
        except Exception as e:
            self.logger.error(f"Cannot connect to the MQTT broker: {self.broker_address}")
            raise e