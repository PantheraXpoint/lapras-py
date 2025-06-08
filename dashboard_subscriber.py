#!/usr/bin/env python3
"""
Simple MQTT subscriber to monitor dashboard state updates from ContextRuleManager.
Subscribes to 'dashboard/context/state' topic and prints received messages.
"""

import json
import logging
import time
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DashboardSubscriber:
    def __init__(self, mqtt_broker: str = "143.248.57.73", mqtt_port: int = 1883):
        """Initialize the dashboard subscriber."""
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.topic = "dashboard/context/state"
        
        # Set up MQTT client
        client_id = f"DashboardSubscriber-{int(time.time()*1000)}"
        self.mqtt_client = mqtt.Client(client_id=client_id)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect
        
        logger.info(f"Initialized dashboard subscriber with client ID: {client_id}")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            logger.info(f"Successfully connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            # Subscribe to dashboard state updates
            result = self.mqtt_client.subscribe(self.topic, qos=1)
            logger.info(f"Subscribed to topic: {self.topic} (result: {result})")
        else:
            logger.error(f"Failed to connect to MQTT broker. Result code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker. Result code: {rc}")
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_message(self, client, userdata, msg):
        """Callback when message is received."""
        try:
            logger.info(f"Message received on topic: {msg.topic}")
            logger.info(f"QoS: {msg.qos}, Retain: {msg.retain}")
            
            # Parse the JSON message
            message_str = msg.payload.decode('utf-8')
            message_data = json.loads(message_str)
            
            # Print the message structure
            print("\n" + "="*80)
            print(f"DASHBOARD STATE UPDATE - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*80)
            
            # Print event metadata
            if 'event' in message_data:
                event = message_data['event']
                print(f"Event ID: {event.get('id', 'N/A')}")
                print(f"Event Type: {event.get('type', 'N/A')}")
                print(f"Event Timestamp: {event.get('timestamp', 'N/A')}")
            
            # Print source and target
            if 'source' in message_data:
                source = message_data['source']
                print(f"Source: {source.get('entityType', 'N/A')} - {source.get('entityId', 'N/A')}")
            
            if 'target' in message_data:
                target = message_data['target']
                print(f"Target: {target.get('entityType', 'N/A')} - {target.get('entityId', 'N/A')}")
            
            # Print payload information
            if 'payload' in message_data:
                payload = message_data['payload']
                
                # Print summary
                if 'summary' in payload:
                    summary = payload['summary']
                    print(f"\nSUMMARY:")
                    print(f"  Total Agents: {summary.get('total_agents', 0)}")
                    print(f"  Known Agents: {summary.get('known_agents', [])}")
                    print(f"  Last Update: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(summary.get('last_update', 0)))}")
                
                # Print agent details
                if 'agents' in payload and payload['agents']:
                    print(f"\nAGENT DETAILS:")
                    for agent_id, agent_info in payload['agents'].items():
                        print(f"\n  Agent: {agent_id}")
                        print(f"    Type: {agent_info.get('agent_type', 'N/A')}")
                        print(f"    Responsive: {agent_info.get('is_responsive', False)}")
                        print(f"    Last Update: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(agent_info.get('last_update', 0)))}")
                        
                        # Print state
                        if 'state' in agent_info:
                            print(f"    State:")
                            for key, value in agent_info['state'].items():
                                print(f"      {key}: {value}")
                        
                        # Print sensors
                        if 'sensors' in agent_info and agent_info['sensors']:
                            print(f"    Sensors:")
                            for sensor_key, sensor_value in agent_info['sensors'].items():
                                print(f"      {sensor_key}: {sensor_value}")
                else:
                    print(f"\nNo agents currently connected.")
            
            print("="*80 + "\n")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            logger.error(f"Raw message: {msg.payload.decode('utf-8', errors='ignore')}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.error(f"Raw message: {msg.payload.decode('utf-8', errors='ignore')}")

    def start(self):
        """Start the subscriber."""
        try:
            logger.info(f"Connecting to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}...")
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port)
            logger.info("Starting MQTT client loop...")
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            logger.info("Subscriber interrupted by user")
        except Exception as e:
            logger.error(f"Error starting subscriber: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the subscriber."""
        logger.info("Stopping dashboard subscriber...")
        if hasattr(self, 'mqtt_client') and self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        logger.info("Dashboard subscriber stopped.")

def main():
    """Main function to run the dashboard subscriber."""
    print("Dashboard State Subscriber")
    print("=" * 50)
    print("This program will subscribe to 'dashboard/context/state' topic")
    print("and display all dashboard state updates from the ContextRuleManager.")
    print("Press Ctrl+C to stop.\n")
    
    subscriber = DashboardSubscriber()
    subscriber.start()

if __name__ == "__main__":
    main() 