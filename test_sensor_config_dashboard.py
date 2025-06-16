#!/usr/bin/env python3
"""
Simple Dashboard Program for testing sensor configuration commands.
This program sends sensor configuration commands to the context rule manager.
"""

import argparse
import json
import logging
import sys
import time
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import paho.mqtt.client as mqtt
from lapras_middleware.event import EventFactory, MQTTMessage, TopicManager

logger = logging.getLogger(__name__)

class SensorConfigDashboard:
    def __init__(self, mqtt_broker="143.248.57.73", mqtt_port=1883):
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        
        # Set up MQTT client
        self.mqtt_client = mqtt.Client(client_id="SensorConfigDashboard", clean_session=True)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        
        # Connect to MQTT broker
        try:
            self.mqtt_client.connect(mqtt_broker, mqtt_port)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT broker at {mqtt_broker}:{mqtt_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            logger.info("Successfully connected to MQTT broker")
            # Subscribe to sensor config results
            result_topic = TopicManager.dashboard_sensor_config_result()
            client.subscribe(result_topic, qos=1)
            logger.info(f"Subscribed to results topic: {result_topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker. Result code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback when message is received."""
        try:
            if msg.topic == TopicManager.dashboard_sensor_config_result():
                event = MQTTMessage.deserialize(msg.payload.decode())
                payload = event.payload
                
                print(f"\n=== SENSOR CONFIG RESULT ===")
                print(f"Command ID: {payload.get('command_id')}")
                print(f"Agent ID: {payload.get('agent_id')}")
                print(f"Action: {payload.get('action')}")
                print(f"Success: {payload.get('success')}")
                print(f"Message: {payload.get('message')}")
                print(f"Current Sensors: {payload.get('current_sensors', [])}")
                print("============================\n")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def send_sensor_config_command(self, agent_id: str, action: str, sensor_config: dict = None):
        """Send a sensor configuration command."""
        try:
            # Create sensor config event
            config_event = EventFactory.create_sensor_config_event(
                target_agent_id=agent_id,
                action=action,
                sensor_config=sensor_config or {},
                source_entity_id="TestDashboard"
            )
            
            # Send to context manager
            command_topic = TopicManager.dashboard_sensor_config_command()
            command_message = MQTTMessage.serialize(config_event)
            self.mqtt_client.publish(command_topic, command_message, qos=1)
            
            print(f"\n=== SENT SENSOR CONFIG COMMAND ===")
            print(f"Command ID: {config_event.event.id}")
            print(f"Target Agent: {agent_id}")
            print(f"Action: {action}")
            if sensor_config:
                print(f"Sensor Config: {sensor_config}")
            print("==================================\n")
            
            logger.info(f"Sent sensor config command to {agent_id}: {action}")
            return config_event.event.id
            
        except Exception as e:
            logger.error(f"Error sending sensor config command: {e}")
            return None
    
    def stop(self):
        """Stop the dashboard."""
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        logger.info("Dashboard stopped")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Test dashboard for sensor configuration commands')
    parser.add_argument('--mqtt-broker', default="143.248.57.73",
                       help='MQTT broker address (default: 143.248.57.73)')
    parser.add_argument('--mqtt-port', type=int, default=1883,
                       help='MQTT broker port (default: 1883)')
    parser.add_argument('--agent-id', required=True,
                       help='Target agent ID for sensor configuration')
    parser.add_argument('--action', choices=['configure', 'add', 'remove', 'list'], required=True,
                       help='Sensor configuration action')
    parser.add_argument('--sensors', nargs='*',
                       help='Sensor configuration. Format: sensor_type:sensor1,sensor2')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse sensor configuration
    sensor_config = {}
    if args.sensors:
        for sensor_arg in args.sensors:
            if ':' in sensor_arg:
                sensor_type, sensors_str = sensor_arg.split(':', 1)
                sensor_ids = [s.strip() for s in sensors_str.split(',')]
                sensor_config[sensor_type] = sensor_ids
            else:
                print(f"Invalid sensor format: {sensor_arg}. Expected format: sensor_type:sensor1,sensor2")
                return 1
    
    try:
        # Create dashboard
        dashboard = SensorConfigDashboard(args.mqtt_broker, args.mqtt_port)
        
        # Wait a moment for connection to establish
        time.sleep(1)
        
        # Send command
        command_id = dashboard.send_sensor_config_command(
            agent_id=args.agent_id,
            action=args.action,
            sensor_config=sensor_config if sensor_config else None
        )
        
        if command_id:
            print(f"Waiting for response (Command ID: {command_id})...")
            print("Press Ctrl+C to exit\n")
            
            # Wait for response
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nExiting...")
        
        dashboard.stop()
        return 0
        
    except Exception as e:
        logger.error(f"Error in dashboard: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 