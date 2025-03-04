from Phidget22.Phidget import Phidget
from Phidget22.Devices.InterfaceKit import InterfaceKit
import time

# Create and open the InterfaceKit
kit = InterfaceKit()

# Print sensor data when it changes
def on_sensor_change(kit, index, value):
    print(f"Sensor {index} value: {value}")

kit.setOnSensorChangeHandler(on_sensor_change)

# Open the first attached InterfaceKit
kit.openWaitForAttachment(5000)

print(f"Connected to: {kit.getDeviceName()} (S/N: {kit.getDeviceSerialNumber()})")

# Keep the program running to receive sensor values
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Closing...")
    kit.close()