import logging
from typing import Optional, List
import paho.mqtt.client as mqtt

from core import Component, Agent
from events.events import EventType, Event, EventDispatcher
from .topic import LaprasTopic

logger = logging.getLogger(__name__)

class MqttCommunicator(Component):
    def __init__(self, event_dispatcher: 'EventDispatcher', agent: 'Agent'):
        super().__init__(event_dispatcher, agent)
        self.broker_address = agent.agent_config.get_option("mqtt_broker")
        self.client_id = agent.agent_config.agent_name
        
        self.mqtt_client = mqtt.Client(self.client_id)
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_connect = self._on_connect
        
    def set_will(self, topic: LaprasTopic, payload: bytes, qos: int, retain: bool):
        """Set the last will message."""
        self.mqtt_client.will_set(str(topic), payload, qos, retain)