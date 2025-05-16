import json
import logging
from typing import Any, Callable, Dict, Optional
import paho.mqtt.client as mqtt
from dataclasses import dataclass
from datetime import datetime

from .component import Component
from .event import Event, EventDispatcher
# from .agent import Agent

logger = logging.getLogger(__name__)

@dataclass
class MqttMessage:
    """Represents an MQTT message."""
    topic: str
    payload: Any
    qos: int = 0
    retain: bool = False

class MqttCommunicator(Component):
    """Handles MQTT communication for the agent."""
    
    def __init__(self, event_dispatcher, agent):
        """Initialize the MQTT communicator."""
        super().__init__(event_dispatcher, agent)
        
        # Get MQTT configuration from agent config
        self.broker_host = agent.agent_config.get_option('mqtt_broker_host', 'localhost')
        self.broker_port = int(agent.agent_config.get_option('mqtt_broker_port', '1883'))
        self.client_id = f"{agent.agent_config.agent_name}_{datetime.now().timestamp()}"
        
        # Initialize MQTT client
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        
    def start(self) -> None:
        """Start the MQTT communicator."""
        try:
            self.client.connect(self.broker_host, self.broker_port)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}", exc_info=True)
            raise
            
    def stop(self) -> None:
        """Stop the MQTT communicator."""
        self.client.loop_stop()
        self.client.disconnect()
        
    def subscribe(self, topic: str, handler: Callable) -> None:
        """Subscribe to an MQTT topic with a message handler."""
        self.message_handlers[topic] = handler
        self.client.subscribe(topic)
        
    def publish(self, message: MqttMessage) -> None:
        """Publish a message to an MQTT topic."""
        try:
            payload = json.dumps(message.payload) if isinstance(message.payload, (dict, list)) else str(message.payload)
            self.client.publish(
                message.topic,
                payload=payload,
                qos=message.qos,
                retain=message.retain
            )
        except Exception as e:
            logger.error(f"Failed to publish message: {e}", exc_info=True)
            
    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Dict, rc: int) -> None:
        """Handle MQTT client connection."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Resubscribe to topics
            for topic in list(self.message_handlers.keys()):
                self.client.subscribe(topic)
        else:
            logger.error(f"Failed to connect to MQTT broker with code: {rc}")
            
    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Handle incoming MQTT messages."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Try to parse JSON payload
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                pass
                
            # Create event
            event = Event(
                type="MQTT_MESSAGE",
                data={
                    'topic': topic,
                    'payload': payload
                },
                timestamp=int(datetime.now().timestamp() * 1000)
            )
            
            # Dispatch event
            self.event_dispatcher.dispatch(event)
            
            # Call message handler if exists
            if topic in self.message_handlers:
                self.message_handlers[topic](payload)
                
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}", exc_info=True)
            
    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """Handle MQTT client disconnection."""
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker with code: {rc}")
        else:
            logger.info("Disconnected from MQTT broker") 