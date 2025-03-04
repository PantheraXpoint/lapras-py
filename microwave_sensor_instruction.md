# Microwave Sensor Demo Instructions

This document describes how to set up and run the Microwave Sensor demo application.

## Prerequisites

1. Python 3.6 or higher
2. An MQTT broker (e.g., Mosquitto)
3. The LAPRAS Python library (including all components we've implemented)

## Installation

1. Install the required Python packages:

```bash
pip install paho-mqtt
```

2. Install an MQTT broker if you don't have one:

   - **Ubuntu**: `sudo apt install mosquitto`
   - **macOS**: `brew install mosquitto`
   - **Windows**: Download from [mosquitto.org/download](https://mosquitto.org/download/)

3. Start the MQTT broker:

```bash
mosquitto -v
```

## Running the Demo

You can run the microwave sensor demo in two ways:

### Option 1: Using the interactive demo script

This is the simplest way to test the microwave sensor:

```bash
python microwave_demo.py
```

Options:

- `--broker`: MQTT broker address (default: localhost:1883)
- `--threshold`: Sensor threshold value (default: 500)

Example:

```bash
python microwave_demo.py --broker localhost:1883 --threshold 600
```

The interactive demo lets you:
1. Simulate opening the microwave door
2. Simulate closing the microwave door
3. Manually invoke the ChangeState functionality
4. Check the current state
5. Exit the demo

### Option 2: Using the configuration file and main application

This approach is closer to how you would run a real LAPRAS agent:

1. Edit the `microwave.ini` file to set your MQTT broker and other parameters
2. Run the main application:

```bash
python lapras_main.py microwave.ini
```

With this approach, you'll need to use an MQTT client to:
- Monitor the MicrowaveState context
- Send functionality invocation messages

## Monitoring MQTT Messages

To monitor the MQTT messages (contexts and functionality invocations), you can use a tool like MQTT Explorer or mosquitto_sub:

```bash
mosquitto_sub -t 'kitchen/#' -v
```

## Simulating with Real Hardware

In a real implementation, you would:

1. Replace the simulated sensor readings with actual Phidget hardware integration
2. Install the appropriate Phidget Python library
3. Modify the PhidgetSensorAgent to use the real hardware API

## Directory Structure

Your project should have the following structure:

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
└── functionality/
    └── (functionality components)

microwave_demo.py
microwave.ini
lapras_main.py
```

## Troubleshooting

1. **MQTT Connection Issues**: 
   - Ensure the MQTT broker is running
   - Check that the broker address is correct
   - Verify that there are no firewall issues

2. **Import Errors**:
   - Make sure your Python path includes the project directory
   - Check that all required files are in the correct locations

3. **No sensor values changing**:
   - In the interactive demo, use options 1 and 2 to manually change sensor values