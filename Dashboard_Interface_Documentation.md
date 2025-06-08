# Dashboard Interface Documentation

## Overview
This document describes the MQTT interface available for dashboard development in the lapras-py IoT system. The system uses a unified Event structure for all MQTT communications, providing consistent message formats across the entire system.

## MQTT Broker Connection
- **Host**: `143.248.57.73`  
- **Port**: `1883` (MQTT) / `9001` (WebSocket for web dashboards)
- **QoS**: 1 (reliable delivery recommended)

## Event Structure
All MQTT messages use the standardized Event structure from `lapras_middleware/event.py`:

```python
@dataclass
class Event:
    event: EventMetadata      # id, timestamp, type, location, priority
    source: EntityInfo        # entityType, entityId  
    payload: Dict[str, Any]   # Flexible data container
    # Note: target field removed - routing handled by MQTT topics
```

## Dashboard MQTT Topics

### 📥 Receiving Data (Dashboard Subscribes)

#### 1. System State Updates
**Topic**: `dashboard/context/state`  
**Event Type**: `dashboardStateUpdate`  
**Frequency**: Real-time (every time any device state changes)

```json
{
  "event": {
    "id": "abc12345",
    "timestamp": "2024-01-15T10:30:00Z",
    "type": "dashboardStateUpdate",
    "location": null,
    "contextType": null,
    "priority": "Normal"
  },
  "source": {
    "entityType": "contextManager",
    "entityId": "CM-MainController"
  },
  "payload": {
    "agents": {
      "VA-AirCon-LivingRoom": {
        "state": {
          "power": "on",
          "temperature": 22,
          "mode": "cool",
          "fan_speed": "medium"
        },
        "agent_type": "aircon",
        "sensors": {
          "TEMP-LivingRoom-01": {
            "sensor_type": "temperature",
            "value": 25.5,
            "unit": "celsius",
            "metadata": null,
            "timestamp": "2024-01-15T10:30:00Z"
          }
        },
        "timestamp": "2024-01-15T10:30:00Z",
        "last_update": 1705317000.123,
        "is_responsive": true
      },
      "VA-Light-Kitchen": {
        "state": {
          "power": "off",
          "brightness": 0,
          "color": "#FFFFFF"
        },
        "agent_type": "light",
        "sensors": {
          "MOTION-Kitchen-01": {
            "sensor_type": "infrared", 
            "value": false,
            "unit": null,
            "metadata": {"proximity_status": "clear"},
            "timestamp": "2024-01-15T10:29:45Z"
          }
        },
        "timestamp": "2024-01-15T10:29:45Z",
        "last_update": 1705316985.456,
        "is_responsive": true
      }
    },
    "summary": {
      "total_agents": 2,
      "known_agents": ["VA-AirCon-LivingRoom", "VA-Light-Kitchen"],
      "last_update": 1705317000.123
    }
  }
}
```

#### 2. Command Results
**Topic**: `dashboard/control/result`  
**Event Type**: `dashboardCommandResult`  
**Frequency**: Immediate response to each command

```json
{
  "event": {
    "id": "def67890",
    "timestamp": "2024-01-15T10:31:01Z", 
    "type": "dashboardCommandResult",
    "location": null,
    "contextType": null,
    "priority": "Normal"
  },
  "source": {
    "entityType": "contextManager",
    "entityId": "CM-MainController"
  },
  "payload": {
    "command_id": "cmd-12345",
    "success": true,
    "message": "Command 'set_temperature' sent to VA-AirCon-LivingRoom",
    "agent_id": "VA-AirCon-LivingRoom",
    "action_event_id": "ghi98765"
  }
}
```

### 📤 Sending Commands (Dashboard Publishes)

#### Manual Device Control
**Topic**: `dashboard/control/command`  
**Event Type**: `dashboardCommand`

```json
{
  "event": {
    "id": "cmd-12345",
    "timestamp": "2024-01-15T10:31:00Z",
    "type": "dashboardCommand",
    "location": null,
    "contextType": null,
    "priority": "High"
  },
  "source": {
    "entityType": "dashboard",
    "entityId": "dashboard-client" 
  },
  "payload": {
    "agent_id": "VA-AirCon-LivingRoom",
    "action_name": "set_temperature",
    "parameters": {
      "temperature": 20
    },
    "priority": "High"
  }
}
```

## Python Dashboard Client

```python
import paho.mqtt.client as mqtt
import json
import time
import uuid
from typing import Dict, Any, Callable, Optional

class DashboardClient:
    def __init__(self, mqtt_broker: str = "143.248.57.73", mqtt_port: int = 1883):
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.current_state = {}
        self.command_callbacks = {}
        
        # Set up MQTT client
        client_id = f"Dashboard-{int(time.time()*1000)}"
        self.mqtt_client = mqtt.Client(client_id=client_id)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        
        # Connect to MQTT broker
        self.mqtt_client.connect(mqtt_broker, mqtt_port)
        self.mqtt_client.loop_start()
        
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            print("Dashboard connected to MQTT broker")
            client.subscribe("dashboard/context/state", qos=1)
            client.subscribe("dashboard/control/result", qos=1)
        else:
            print(f"Failed to connect. Result code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        try:
            # Parse Event structure
            event_data = json.loads(msg.payload.decode())
            event_type = event_data["event"]["type"]
            payload = event_data["payload"]
            
            if event_type == "dashboardStateUpdate":
                self._handle_state_update(payload)
            elif event_type == "dashboardCommandResult":
                self._handle_command_result(payload)
                
        except json.JSONDecodeError:
            print(f"Invalid JSON received on topic {msg.topic}")
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def _handle_state_update(self, payload: Dict[str, Any]):
        """Handle system state update."""
        self.current_state = payload
        print(f"State updated: {payload['summary']['total_agents']} agents")
        # Add your UI update logic here
    
    def _handle_command_result(self, payload: Dict[str, Any]):
        """Handle command execution result.""" 
        command_id = payload.get('command_id')
        success = payload.get('success')
        message = payload.get('message')
        
        print(f"Command {command_id}: {'SUCCESS' if success else 'FAILED'} - {message}")
        
        # Call registered callback if exists
        if command_id in self.command_callbacks:
            callback = self.command_callbacks.pop(command_id)
            callback(payload)
    
    def send_command(self, agent_id: str, action_name: str,
                    parameters: Optional[Dict[str, Any]] = None,
                    priority: str = "High",
                    callback: Optional[Callable] = None) -> str:
        """Send control command to an agent using Event structure."""
        command_id = f"cmd-{uuid.uuid4().hex[:8]}"
        
        # Create Event structure for command
        command_event = {
            "event": {
                "id": command_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "type": "dashboardCommand",
                "location": None,
                "contextType": None,
                "priority": priority
            },
            "source": {
                "entityType": "dashboard",
                "entityId": "dashboard-client"
            },
            "payload": {
                "agent_id": agent_id,
                "action_name": action_name,
                "priority": priority
            }
        }
        
        if parameters:
            command_event["payload"]["parameters"] = parameters
        
        # Register callback if provided
        if callback:
            self.command_callbacks[command_id] = callback
        
        # Publish command
        command_message = json.dumps(command_event)
        self.mqtt_client.publish("dashboard/control/command", command_message, qos=1)
        
        print(f"Sent command {command_id}: {action_name} to {agent_id}")
        return command_id
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get the current system state."""
        return self.current_state
    
    def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get state of a specific agent."""
        agents = self.current_state.get('agents', {})
        return agents.get(agent_id)
    
    def stop(self):
        """Stop the dashboard client."""
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        print("Dashboard client stopped")

# Usage Example
dashboard = DashboardClient()
time.sleep(2)  # Wait for initial state

# Control devices
dashboard.send_command("VA-AirCon-LivingRoom", "turn_on")
dashboard.send_command("VA-AirCon-LivingRoom", "set_temperature", {"temperature": 22})
dashboard.send_command("VA-Light-Kitchen", "set_brightness", {"brightness": 80})
```

## JavaScript Web Dashboard

```html
<!DOCTYPE html>
<html>
<head>
    <title>IoT Dashboard</title>
    <script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
</head>
<body>
    <div id="dashboard">
        <h1>IoT System Dashboard</h1>
        <div id="agents"></div>
        <div id="controls">
            <button onclick="turnOnAircon()">Turn On Air Conditioner</button>
            <button onclick="setTemperature(20)">Set Temperature to 20°C</button>
            <button onclick="turnOnLight()">Turn On Kitchen Light</button>
        </div>
    </div>

    <script>
        class WebDashboard {
            constructor() {
                // Connect to MQTT broker via WebSocket
                this.client = mqtt.connect('ws://143.248.57.73:9001');
                this.currentState = {};
                
                this.client.on('connect', () => {
                    console.log('Connected to MQTT broker');
                    this.client.subscribe('dashboard/context/state');
                    this.client.subscribe('dashboard/control/result');
                });
                
                this.client.on('message', (topic, message) => {
                    const eventData = JSON.parse(message.toString());
                    const eventType = eventData.event.type;
                    const payload = eventData.payload;
                    
                    if (eventType === 'dashboardStateUpdate') {
                        this.handleStateUpdate(payload);
                    } else if (eventType === 'dashboardCommandResult') {
                        this.handleCommandResult(payload);
                    }
                });
            }
            
            sendCommand(agentId, actionName, parameters = null) {
                const commandId = 'cmd-' + Math.random().toString(36).substr(2, 8);
                
                // Create Event structure
                const commandEvent = {
                    event: {
                        id: commandId,
                        timestamp: new Date().toISOString(),
                        type: 'dashboardCommand',
                        location: null,
                        contextType: null,
                        priority: 'High'
                    },
                    source: {
                        entityType: 'dashboard',
                        entityId: 'dashboard-client'
                    },
                    payload: {
                        agent_id: agentId,
                        action_name: actionName,
                        priority: 'High'
                    }
                };
                
                if (parameters) {
                    commandEvent.payload.parameters = parameters;
                }
                
                this.client.publish('dashboard/control/command', JSON.stringify(commandEvent));
                console.log('Sent command:', commandEvent);
                return commandId;
            }
            
            handleStateUpdate(payload) {
                this.currentState = payload;
                this.updateUI();
            }
            
            handleCommandResult(payload) {
                console.log('Command result:', payload);
                const message = payload.success ? 
                    `Success: ${payload.message}` : 
                    `Failed: ${payload.message}`;
                this.showNotification(message, payload.success ? 'success' : 'error');
            }
            
            updateUI() {
                const agentsDiv = document.getElementById('agents');
                agentsDiv.innerHTML = '';
                
                if (this.currentState.agents) {
                    for (const [agentId, agentData] of Object.entries(this.currentState.agents)) {
                        const agentDiv = document.createElement('div');
                        agentDiv.className = 'agent-card';
                        agentDiv.innerHTML = `
                            <h3>${agentId}</h3>
                            <p>Type: ${agentData.agent_type}</p>
                            <p>Power: ${agentData.state.power || 'unknown'}</p>
                            <p>Responsive: ${agentData.is_responsive ? 'Yes' : 'No'}</p>
                            <pre>${JSON.stringify(agentData.state, null, 2)}</pre>
                        `;
                        agentsDiv.appendChild(agentDiv);
                    }
                }
            }
            
            showNotification(message, type) {
                const notification = document.createElement('div');
                notification.className = `notification ${type}`;
                notification.textContent = message;
                document.body.appendChild(notification);
                
                setTimeout(() => {
                    document.body.removeChild(notification);
                }, 3000);
            }
        }
        
        const dashboard = new WebDashboard();
        
        function turnOnAircon() {
            dashboard.sendCommand('VA-AirCon-LivingRoom', 'turn_on');
        }
        
        function setTemperature(temp) {
            dashboard.sendCommand('VA-AirCon-LivingRoom', 'set_temperature', {temperature: temp});
        }
        
        function turnOnLight() {
            dashboard.sendCommand('VA-Light-Kitchen', 'turn_on');
        }
    </script>
    
    <style>
        .agent-card {
            border: 1px solid #ccc;
            margin: 10px;
            padding: 10px;
            border-radius: 5px;
        }
        .notification {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 10px;
            border-radius: 5px;
            color: white;
        }
        .notification.success { background-color: green; }
        .notification.error { background-color: red; }
    </style>
</body>
</html>
```

## Common Device Actions

### Air Conditioner
```python
# Power control
dashboard.send_command("VA-AirCon-LivingRoom", "turn_on")
dashboard.send_command("VA-AirCon-LivingRoom", "turn_off")

# Temperature control
dashboard.send_command("VA-AirCon-LivingRoom", "set_temperature", {"temperature": 20})

# Mode control  
dashboard.send_command("VA-AirCon-LivingRoom", "set_mode", {"mode": "cool"})
```

### Light
```python
# Power control
dashboard.send_command("VA-Light-Kitchen", "turn_on")
dashboard.send_command("VA-Light-Kitchen", "turn_off")

# Brightness control (0-100)
dashboard.send_command("VA-Light-Kitchen", "set_brightness", {"brightness": 80})

# Color control (hex code)
dashboard.send_command("VA-Light-Kitchen", "set_color", {"color": "#FF5733"})
```

### Microwave
```python
# Start timer
dashboard.send_command("VA-Microwave-Kitchen", "start_timer", {
    "duration": 120, 
    "power_level": 80
})

# Stop
dashboard.send_command("VA-Microwave-Kitchen", "stop")
```

## Testing Commands

### Monitor Dashboard Topics
```bash
# Subscribe to all dashboard topics
mosquitto_sub -h 143.248.57.73 -t "dashboard/#" -v

# Monitor state updates only
mosquitto_sub -h 143.248.57.73 -t "dashboard/context/state" -v
```

### Send Test Command
```bash
mosquitto_pub -h 143.248.57.73 -t "dashboard/control/command" -m '{
  "event": {
    "id": "test-001",
    "timestamp": "2024-01-15T10:31:00Z", 
    "type": "dashboardCommand",
    "location": null,
    "contextType": null,
    "priority": "High"
  },
  "source": {
    "entityType": "dashboard",
    "entityId": "dashboard-client"
  },
  "payload": {
    "agent_id": "VA-AirCon-LivingRoom",
    "action_name": "turn_on",
    "priority": "High"
  }
}'
```

## Available Data for Dashboard

### Real-time Device States
- Current power status (on/off)
- Device-specific settings (temperature, brightness, etc.)
- Operating modes and configurations
- Connection status and responsiveness

### Sensor Data
- Temperature readings
- Motion detection status
- Humidity levels
- Any other sensor values attached to devices

### System Information
- Total number of connected devices
- List of known agents
- Last update timestamps
- Device responsiveness indicators

### Command Feedback
- Command execution success/failure
- Error messages and debugging info
- Action confirmation with timestamps

## Benefits

✅ **Consistent Event Structure**: All messages use the same standardized format  
✅ **Real-time Updates**: Immediate state changes via MQTT  
✅ **Reliable Delivery**: QoS 1 ensures message delivery  
✅ **Structured Metadata**: Event IDs, timestamps, priorities included  
✅ **Cross-platform**: Works with any MQTT client  
✅ **Type Safety**: Well-defined message structures  
✅ **Scalable**: Multiple dashboards can connect simultaneously  

This interface provides everything needed to build a comprehensive IoT dashboard with real-time monitoring and device control capabilities. 