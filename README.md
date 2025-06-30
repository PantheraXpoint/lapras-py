# LAPRAS: A Smart Middleware for IoT enabled Urban Spaces

For detailed information about Lapras, a developer documentation, as well as quick start guides, please consult the [Lapras Wiki](https://github.com/PantheraXpoint/lapras-py/wiki)!

## Dashboard Development

📱 **For Dashboard/Frontend Developers**: See **[Dashboard Interface Documentation](Dashboard_Interface_Documentation.md)** for complete MQTT interface, message formats, and code examples for building dashboard applications.

The dashboard interface provides:
- Real-time device state monitoring via MQTT
- Manual device control commands  
- Standardized Event message structure
- Python and JavaScript client examples
- WebSocket support for web dashboards

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
