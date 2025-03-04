# LAPRAS Microwave Sensor Project Guide

This guide explains how to set up and run the LAPRAS Microwave Sensor project, which monitors a microwave door using Phidget sensors.

## 1. Project Overview

The project is a Python implementation of the LAPRAS middleware, focused on a microwave door sensor application. It consists of:

- Core framework components (Agent, EventDispatcher, etc.)
- Sensor integration with Phidget hardware
- Microwave door monitoring agent
- Configuration files
- Testing and demo tools

## 2. Key Files and Their Roles

### Core Framework Files
These are the foundation of the LAPRAS system that you don't directly interact with, but power everything:

- **agent/component.py**: Base class for all components with event handling
- **agent/agent.py**: Core agent class that manages components
- **agent/agent_component.py**: Base class for agent components with functionality methods
- **event/**, **context/**, **communicator/**, etc.: Supporting subsystems

### Implementation Files
These implement the specific microwave sensor functionality:

- **agents/phidget/phidget_sensor_agent.py**: 
  - Handles interfacing with Phidget hardware
  - Manages sensor configuration and callbacks
  - Abstracts hardware interaction

- **agents/microwave/microwave_agent.py**:
  - Implements the microwave door monitoring logic
  - Contains the threshold logic for door state detection
  - Provides the ChangeState functionality

### Configuration Files

- **microwave.ini**:
  - Contains all configuration for the microwave agent
  - Specifies MQTT broker address
  - Sets sensor thresholds and behavior
  - Defines which sensors to use
  - Example:
    ```ini
    agent_name = MicrowaveMonitor
    broker_address = localhost:1883
    phidget_serial = -1
    threshold = 500
    ```

### Runner and Demo Tools

- **lapras_main.py**: 
  - The main application launcher
  - Loads configuration from .ini files
  - Instantiates and starts agents based on config
  - Used for production-style deployment
  - Command: `python lapras_main.py microwave.ini`

- **microwave_demo.py**:
  - Interactive demo script for testing
  - Simulates sensor values through console
  - Good for development and testing
  - Command: `python microwave_demo.py --threshold 500`

- **microwave_agent_tester.py**:
  - Advanced testing tool with UI
  - Monitors MQTT messages
  - Runs automated tests
  - Provides visual feedback
  - Command: `python microwave_agent_tester.py`

## 3. Installation

### Prerequisites
- Python 3.6 or higher
- MQTT broker (e.g., Mosquitto)
- Phidget hardware (for real sensor deployment)

### Installing Dependencies

```bash
# Install MQTT client
pip install paho-mqtt

# Install Phidget library (for real hardware)
pip install Phidget22

# Install Phidget drivers for your OS
# See: https://www.phidgets.com/docs/Operating_System_Support
```

### Setting Up MQTT Broker

```bash
# Ubuntu
sudo apt install mosquitto mosquitto-clients

# macOS
brew install mosquitto

# Windows
# Download from https://mosquitto.org/download/

# Start the broker
mosquitto -v
```

## 4. How to Run the Project

### Option 1: Using the Interactive Demo

This is best for development and testing without real hardware:

```bash
python microwave_demo.py
```

The demo script will:
1. Create a MicrowaveAgent with simulated sensors
2. Connect to the MQTT broker
3. Provide an interactive menu to simulate door opening/closing
4. Allow you to invoke the ChangeState functionality
5. Show the current state

Command-line options:
```bash
python microwave_demo.py --broker localhost:1883 --threshold 600
```

### Option 2: Using the Configuration-Based Runner

This is more similar to a production deployment:

```bash
python lapras_main.py microwave.ini
```

This approach:
1. Reads the microwave.ini configuration file
2. Creates the exact agent structure specified in the config
3. Connects to the specified MQTT broker
4. Runs in the background, monitoring sensor values
5. Publishes state changes to MQTT topics

### Option 3: Using the UI-Based Tester

This is best for demonstration and comprehensive testing:

```bash
python microwave_agent_tester.py
```

This tool:
1. Provides a visual interface showing agent state
2. Connects to the MQTT broker to monitor messages
3. Allows triggering the ChangeState functionality
4. Runs automated test sequences
5. Displays test results and message history

Command-line options:
```bash
python microwave_agent_tester.py --broker localhost --port 1883 --place kitchen
```

## 5. Real-World Deployment Process

For a full deployment with real hardware:

1. **Connect Hardware**:
   - Connect your Phidget InterfaceKit to the computer
   - Attach the appropriate sensor to the InterfaceKit
   - Position the sensor to detect the microwave door

2. **Configure the Agent**:
   - Edit microwave.ini with your specific settings
   - Set the correct Phidget serial number
   - Adjust the threshold based on your sensor readings

3. **Start the MQTT Broker**:
   ```bash
   mosquitto -v
   ```

4. **Launch the Agent**:
   ```bash
   python lapras_main.py microwave.ini
   ```

5. **Monitor and Test**:
   ```bash
   python microwave_agent_tester.py
   ```

6. **Verify Operation**:
   - Open and close the microwave door
   - Confirm state changes in the tester UI
   - Check MQTT messages being published

## 6. Troubleshooting

### Common Issues:

1. **MQTT Connection Failed**
   - Ensure the MQTT broker is running
   - Check that the broker address is correct
   - Verify there are no firewall issues

2. **No Sensor Detection**
   - Check USB connection for Phidget hardware
   - Verify the serial number in configuration
   - Ensure drivers are installed correctly
   - Try a different USB port

3. **Incorrect State Detection**
   - Recalibrate your threshold value
   - Check sensor positioning
   - Add debouncing if readings fluctuate

4. **Import Errors**
   - Make sure all components are in the correct directory structure
   - Check for missing dependencies

### Monitoring MQTT Messages

Use mosquitto_sub or MQTT Explorer to monitor the messages:

```bash
mosquitto_sub -t 'kitchen/#' -v
```

## 7. Project Structure

Your project should have the following directory structure:

```
lapras/
├── __init__.py
├── agent/
│   ├── __init__.py
│   ├── agent.py
│   ├── agent_component.py
│   ├── agent_config.py
│   ├── component.py
│   └── context.py
├── agents/
│   ├── __init__.py
│   ├── microwave/
│   │   ├── __init__.py
│   │   └── microwave_agent.py
│   └── phidget/
│       ├── __init__.py
│       └── phidget_sensor_agent.py
├── communicator/
│   └── (mqtt components)
├── context/
│   └── (context components)
├── event/
│   └── (event components)
├── functionality/
│   └── (functionality components)
├── microwave_demo.py
├── microwave.ini
├── lapras_main.py
└── microwave_agent_tester.py
```

## 8. Additional Resources

- [Phidget Documentation](https://www.phidgets.com/docs/Main_Page)
- [MQTT Documentation](https://mqtt.org/documentation/)
- [Mosquitto MQTT Broker](https://mosquitto.org/documentation/)

## 9. Contributing

Feel free to extend the project with:
- Additional sensor types
- More sophisticated state detection algorithms
- Integration with other smart home systems
- User interface improvements

---

This LAPRAS implementation provides a flexible framework for IoT devices and sensor monitoring with a focus on modularity and event-driven design. The microwave sensor example demonstrates the core concepts that can be extended to many other IoT applications.