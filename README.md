# New Agent Architecture: VirtualAgent and SensorAgent

## Overview

This project has been refactored to use a new modular architecture with two main base classes:

- **SensorAgent**: Base class for individual sensors that run as separate processes
- **VirtualAgent**: Base class for devices that manage multiple SensorAgents and control actuators

## Architecture Benefits

1. **Modularity**: Sensors can be easily added, removed, or reused across different virtual agents
2. **Scalability**: Each sensor runs as an independent process
3. **Flexibility**: VirtualAgents can have different sensor combinations and control logic
4. **Separation of Concerns**: Sensor data collection is separate from control logic

## Communication Flow

```
SensorAgent → (MQTT) → VirtualAgent → (MQTT) → ContextRuleManager
                                   ← (MQTT) ← 
```

### MQTT Topics

- **Sensor to Virtual**: `sensor/{sensor_id}/to/{virtual_agent_id}/data`
- **Virtual to Context**: `virtual/{virtual_agent_id}/state`
- **Context to Virtual**: `virtual/{virtual_agent_id}/action`
- **Virtual to Context (results)**: `virtual/{virtual_agent_id}/result`

## Message Structure

All MQTT messages use standardized data structures:

- **SensorData**: Sensor readings with metadata
- **VirtualAgentState**: Combined state of virtual agent and all sensors
- **ActionCommand**: Commands from ContextRuleManager to VirtualAgent
- **ActionResult**: Results of action execution

## Running the System

### 1. Start the ContextRuleManager
```bash
python start_context_rule_manager.py
```

### 2. Start the VirtualAgent (Aircon)
```bash
python start_aircon_agent.py
```

### 3. Start the SensorAgent (Infrared)
```bash
python start_infrared_sensor.py
```

### 4. Test the System (Optional)
```bash
python test_new_architecture.py
```

## Current Implementation: Aircon System

The aircon system consists of:

- **AirconAgent** (VirtualAgent): Manages the air conditioner with control actions
- **InfraredSensorAgent** (SensorAgent): Reads distance data from Phidget IR sensor

### Supported Actions

The AirconAgent supports these action commands:

1. `turn_on` - Turn on the air conditioner
2. `turn_off` - Turn off the air conditioner  
3. `set_temperature` - Set target temperature (parameter: `temperature`)
4. `set_mode` - Set operation mode (parameter: `mode`: auto/cool/heat/fan)

### Example Action Command

```json
{
  "agent_id": "aircon",
  "action_type": "set_temperature",
  "parameters": {
    "temperature": 22
  }
}
```

## Process Architecture

For a complete aircon system, you need to run **3 processes**:

1. **ContextRuleManager** - Central rule engine
2. **AirconAgent** (VirtualAgent) - Air conditioner control
3. **InfraredSensorAgent** (SensorAgent) - Distance sensor

Each process communicates via MQTT on specific topics.

## Adding New Sensors

To add a new sensor to the aircon system:

1. Create a new SensorAgent subclass
2. Implement the required abstract methods:
   - `initialize_sensor()`
   - `cleanup_sensor()`
   - `read_sensor()`
3. Add the sensor to the VirtualAgent using `add_sensor_agent(sensor_id)`
4. Create a start script for the new sensor

## Adding New VirtualAgents

To create a new device type:

1. Create a new VirtualAgent subclass
2. Implement the required abstract methods:
   - `perception()`
   - `execute_action()`
3. Add sensors using `add_sensor_agent()`
4. Define supported action types in `execute_action()`

## File Structure

```
lapras-py/
├── lapras_middleware/
│   ├── virtual_agent.py      # VirtualAgent base class
│   ├── sensor_agent.py       # SensorAgent base class
│   ├── event.py              # Message structures
│   └── ...
├── lapras_agents/
│   ├── aircon_agent.py       # AirconAgent (VirtualAgent)
│   ├── infrared_sensor_agent.py  # InfraredSensorAgent (SensorAgent)
│   └── ...
├── start_aircon_agent.py     # Start AirconAgent
├── start_infrared_sensor.py  # Start InfraredSensorAgent
├── start_context_rule_manager.py  # Start ContextRuleManager
└── test_new_architecture.py  # Test script
```

## Dependencies

- paho-mqtt
- Phidget22 (for hardware sensors)
- Standard Python libraries

## Future Extensions

This architecture easily supports:

- Multiple sensor types per VirtualAgent
- Multiple VirtualAgents in the system
- Sensor sharing between VirtualAgents (different topics)
- Complex control logic in VirtualAgents
- Easy testing and mocking of sensors