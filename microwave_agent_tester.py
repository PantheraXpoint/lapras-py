#!/usr/bin/env python3
"""
Microwave Agent Test & Demo Tool

This script provides a comprehensive testing and demonstration interface
for the LAPRAS Microwave Agent. It connects to the MQTT broker, monitors
the agent's state, and allows for interactive testing.
"""

import paho.mqtt.client as mqtt
import json
import time
import threading
import argparse
import curses
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='microwave_test.log'
)

logger = logging.getLogger("MicrowaveTest")

# Global variables
microwave_state = "Unknown"
last_update_time = None
received_messages = []
last_sensor_value = None

# Test results tracking
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "tests": []
}

class MicrowaveAgentTester:
    def __init__(self, broker_host, broker_port, place_name):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.place_name = place_name
        self.client = None
        self.connected = False
        self.state = "Unknown"
        self.last_update = None
        self.stdscr = None  # curses screen
        self.running = True
        self.messages = []
        self.max_messages = 10  # Max number of messages to display
        self.lock = threading.Lock()
        
    def connect(self):
        """Connect to the MQTT broker and set up callbacks"""
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to broker: {e}")
            return False
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker"""
        if rc == 0:
            self.connected = True
            logger.info("Connected to MQTT broker")
            
            # Subscribe to all topics in the place
            context_topic = f"{self.place_name}/context/#"
            client.subscribe(context_topic)
            logger.info(f"Subscribed to {context_topic}")
            
            # Optional: Subscribe to debug topics that might expose sensor values
            debug_topic = f"{self.place_name}/debug/#"
            client.subscribe(debug_topic)
            
        else:
            logger.error(f"Failed to connect to broker with code {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the broker"""
        self.connected = False
        logger.warning(f"Disconnected from broker with code {rc}")
    
    def on_message(self, client, userdata, msg):
        """Callback for when a message is received from the broker"""
        global microwave_state, last_update_time, received_messages, last_sensor_value
        
        topic = msg.topic
        try:
            payload = msg.payload.decode('utf-8')
            logger.debug(f"Received message on {topic}: {payload}")
            
            # Add to message history
            timestamp = datetime.now().strftime("%H:%M:%S")
            with self.lock:
                self.messages.append(f"{timestamp} | {topic} | {payload[:40]}")
                if len(self.messages) > self.max_messages:
                    self.messages.pop(0)
            
            # Process context messages
            if f"{self.place_name}/context/MicrowaveState" in topic:
                try:
                    data = json.loads(payload)
                    microwave_state = data.get("value", "Unknown")
                    last_update_time = datetime.now().strftime("%H:%M:%S")
                    
                    received_messages.append({
                        "time": last_update_time,
                        "topic": topic,
                        "payload": data
                    })
                    
                    logger.info(f"Microwave state updated: {microwave_state}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse message payload: {payload}")
            
            # Process any debug messages that might contain sensor values
            if "sensor" in topic.lower() or "debug" in topic.lower():
                try:
                    data = json.loads(payload)
                    if "value" in data:
                        last_sensor_value = data["value"]
                        logger.info(f"Sensor value: {last_sensor_value}")
                except (json.JSONDecodeError, KeyError):
                    pass
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def invoke_change_state(self):
        """Invoke the ChangeState functionality on the agent"""
        if not self.connected:
            logger.error("Not connected to broker, cannot invoke functionality")
            return False
        
        topic = f"{self.place_name}/functionality/ChangeState"
        payload = {
            "name": "ChangeState",
            "timestamp": int(time.time() * 1000),
            "publisher": "MicrowaveTester",
            "arguments": []
        }
        
        logger.info(f"Invoking ChangeState functionality")
        self.client.publish(topic, json.dumps(payload))
        return True
    
    def run_automated_test(self, test_type="basic"):
        """Run an automated test suite"""
        global test_results
        
        if not self.connected:
            logger.error("Not connected to broker, cannot run tests")
            return False
        
        logger.info(f"Starting {test_type} test suite")
        
        if test_type == "basic":
            # Basic test: invoke ChangeState and verify state changes
            initial_state = microwave_state
            
            # Record test start
            test = {
                "name": "Basic ChangeState Test",
                "start_time": datetime.now().strftime("%H:%M:%S"),
                "initial_state": initial_state,
                "status": "Running"
            }
            test_results["tests"].append(test)
            test_results["total"] += 1
            
            # Invoke functionality
            self.invoke_change_state()
            
            # Wait for state change
            max_wait = 5  # seconds
            start_time = time.time()
            state_changed = False
            
            while time.time() - start_time < max_wait:
                time.sleep(0.1)
                if microwave_state != initial_state:
                    state_changed = True
                    break
            
            # Record test result
            test["end_time"] = datetime.now().strftime("%H:%M:%S")
            test["final_state"] = microwave_state
            
            if state_changed:
                test["status"] = "Passed"
                test_results["passed"] += 1
                logger.info("Basic test PASSED: State changed as expected")
            else:
                test["status"] = "Failed"
                test_results["failed"] += 1
                logger.error("Basic test FAILED: State did not change")
            
            return state_changed
            
        elif test_type == "rapid":
            # Rapid toggle test: invoke ChangeState multiple times rapidly
            test = {
                "name": "Rapid Toggle Test",
                "start_time": datetime.now().strftime("%H:%M:%S"),
                "initial_state": microwave_state,
                "status": "Running"
            }
            test_results["tests"].append(test)
            test_results["total"] += 1
            
            iterations = 5
            success_count = 0
            
            for i in range(iterations):
                initial_state = microwave_state
                self.invoke_change_state()
                
                # Wait briefly for state change
                time.sleep(0.5)
                
                if microwave_state != initial_state:
                    success_count += 1
                
                # Add short delay between iterations
                time.sleep(0.3)
            
            # Record test result
            test["end_time"] = datetime.now().strftime("%H:%M:%S")
            test["success_rate"] = f"{success_count}/{iterations}"
            
            if success_count == iterations:
                test["status"] = "Passed"
                test_results["passed"] += 1
                logger.info(f"Rapid test PASSED: {success_count}/{iterations} successful toggles")
            else:
                test["status"] = "Failed"
                test_results["failed"] += 1
                logger.error(f"Rapid test PARTIAL FAILURE: {success_count}/{iterations} successful toggles")
            
            return success_count == iterations
            
        return False
    
    def start_ui(self):
        """Start the curses UI"""
        curses.wrapper(self.ui_main)
    
    def ui_main(self, stdscr):
        """Main UI loop using curses"""
        self.stdscr = stdscr
        curses.curs_set(0)  # Hide cursor
        stdscr.timeout(100)  # Non-blocking input with 100ms refresh
        
        # Initialize color pairs
        if curses.has_colors():
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Success/Online
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)    # Error/Offline
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Warning/Notice
            curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Info
        
        # Main UI loop
        while self.running:
            self.update_ui()
            
            # Handle keyboard input
            try:
                key = stdscr.getch()
                if key == ord('q'):
                    self.running = False
                elif key == ord('c'):
                    self.invoke_change_state()
                elif key == ord('t'):
                    self.run_automated_test("basic")
                elif key == ord('r'):
                    self.run_automated_test("rapid")
                elif key == ord('m'):
                    # Force refresh max messages
                    with self.lock:
                        self.max_messages = min(20, self.max_messages + 2)
            except Exception as e:
                logger.error(f"UI input error: {e}")
            
            time.sleep(0.05)  # Small delay to prevent high CPU usage
    
    def update_ui(self):
        """Update the curses UI with current state information"""
        try:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            
            # Title and status
            self.stdscr.addstr(0, 0, "MICROWAVE AGENT TEST & DEMO", curses.A_BOLD)
            
            # Connection status
            status_str = "CONNECTED" if self.connected else "DISCONNECTED"
            status_color = curses.color_pair(1) if self.connected else curses.color_pair(2)
            self.stdscr.addstr(0, max_x - len(status_str) - 2, status_str, status_color | curses.A_BOLD)
            
            # Current state information
            self.stdscr.addstr(2, 0, f"Microwave State: ", curses.A_BOLD)
            state_color = curses.color_pair(1) if microwave_state == "Open" else curses.color_pair(4)
            self.stdscr.addstr(2, 17, f"{microwave_state}", state_color | curses.A_BOLD)
            
            if last_update_time:
                self.stdscr.addstr(3, 0, f"Last Update: {last_update_time}")
            
            if last_sensor_value is not None:
                self.stdscr.addstr(4, 0, f"Last Sensor Value: {last_sensor_value}")
            
            # Commands list
            self.stdscr.addstr(6, 0, "COMMANDS:", curses.A_BOLD)
            self.stdscr.addstr(7, 2, "c - Change State")
            self.stdscr.addstr(8, 2, "t - Run Basic Test")
            self.stdscr.addstr(9, 2, "r - Run Rapid Toggle Test")
            self.stdscr.addstr(10, 2, "q - Quit")
            
            # Test results
            self.stdscr.addstr(12, 0, "TEST RESULTS:", curses.A_BOLD)
            self.stdscr.addstr(13, 2, f"Total: {test_results['total']}")
            
            passed_str = f"Passed: {test_results['passed']}"
            passed_color = curses.color_pair(1) if test_results['passed'] > 0 else curses.A_NORMAL
            self.stdscr.addstr(14, 2, passed_str, passed_color)
            
            failed_str = f"Failed: {test_results['failed']}"
            failed_color = curses.color_pair(2) if test_results['failed'] > 0 else curses.A_NORMAL
            self.stdscr.addstr(15, 2, failed_str, failed_color)
            
            # Message history
            history_y = 17
            self.stdscr.addstr(history_y - 1, 0, "RECENT MESSAGES:", curses.A_BOLD)
            
            with self.lock:
                for i, msg in enumerate(self.messages):
                    if history_y + i < max_y - 1:  # Prevent writing outside window
                        # Truncate message if needed
                        max_msg_length = max_x - 2
                        if len(msg) > max_msg_length:
                            msg = msg[:max_msg_length-3] + "..."
                            
                        self.stdscr.addstr(history_y + i, 0, msg)
            
            # Bottom status line
            self.stdscr.addstr(max_y-1, 0, f"Connected to: {self.broker_host}:{self.broker_port} | Place: {self.place_name}", curses.A_REVERSE)
            
            self.stdscr.refresh()
            
        except curses.error:
            # Ignore errors from writing outside the window
            pass
        except Exception as e:
            logger.error(f"UI update error: {e}")
    
    def disconnect(self):
        """Disconnect from the MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Microwave Agent Tester and Demo Tool')
    parser.add_argument('--broker', default='localhost', help='MQTT broker hostname')
    parser.add_argument('--port', type=int, default=1883, help='MQTT broker port')
    parser.add_argument('--place', default='kitchen', help='Place name for MQTT topics')
    args = parser.parse_args()
    
    # Create and run the tester
    tester = MicrowaveAgentTester(args.broker, args.port, args.place)
    
    if tester.connect():
        try:
            # Start the UI
            tester.start_ui()
        finally:
            tester.disconnect()
    else:
        print("Failed to connect to MQTT broker. Check connection and try again.")
        logger.error("Failed to start tester due to connection failure")


if __name__ == "__main__":
    main()