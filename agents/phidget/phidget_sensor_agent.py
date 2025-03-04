# lapras/agents/phidget/phidget_sensor_agent.py
import logging
import threading
import time
from enum import Enum
from typing import List, Dict, Optional, Any

from Phidget22.Phidget import Phidget
from Phidget22.Devices.InterfaceKit import InterfaceKit
from Phidget22.PhidgetException import PhidgetException

from agent.agent_component import AgentComponent

class PhidgetSensorAgent(AgentComponent):
    """Base class for Phidget sensor agents."""
    
    # SensorInfo class definition remains the same
    class SensorInfo:
        # ... (same as before)
        pass
    
    def __init__(self, event_dispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Get configuration from agent
        self.interface_kit_serial = int(
            agent.get_agent_config().get_option_or_default("phidget_serial", "-1")
        )
        
        # Parse sensor configuration from agent config
        self.sensor_infos = []
        self._parse_sensor_config(agent)
        
        # Create the InterfaceKit object
        self.interface_kit = None
        
        # Thread pool for periodic reading
        self.periodic_read_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.periodic_tasks = []
        
        # Flag to indicate if the interface kit is attached
        self.is_attached = False
    
    def _parse_sensor_config(self, agent):
        # Same as before
        pass
    
    def _init_phidget_interface_kit(self, serial: int):
        """Initialize the Phidget interface kit with real hardware"""
        try:
            self.logger.info(f"Initializing Phidget interface kit with serial: {serial}")
            
            # Create and configure the InterfaceKit
            self.interface_kit = InterfaceKit()
            
            # Set up event handlers
            self.interface_kit.setOnAttachHandler(self._on_attach)
            self.interface_kit.setOnDetachHandler(self._on_detach)
            self.interface_kit.setOnErrorHandler(self._on_error)
            self.interface_kit.setOnSensorChangeHandler(self._on_sensor_change)
            
            # Open the InterfaceKit
            if serial > 0:
                self.interface_kit.setDeviceSerialNumber(serial)
            
            self.interface_kit.openWaitForAttachment(2000)  # Wait up to 2 seconds
            
            self.logger.info(f"Phidget interface kit attached: {self.interface_kit.getDeviceName()}")
            self.is_attached = True
            
        except PhidgetException as e:
            self.logger.error(f"Error initializing Phidget interface kit: {e}")
            raise
    
    def _on_attach(self, kit):
        """Called when the InterfaceKit is attached"""
        self.logger.info(f"InterfaceKit attached: {kit.getDeviceName()} (S/N: {kit.getDeviceSerialNumber()})")
        self.is_attached = True
    
    def _on_detach(self, kit):
        """Called when the InterfaceKit is detached"""
        self.logger.info(f"InterfaceKit detached: {kit.getDeviceName()}")
        self.is_attached = False
    
    def _on_error(self, kit, error_code, error_string):
        """Called when an error occurs with the InterfaceKit"""
        self.logger.error(f"InterfaceKit error: {error_string} (code: {error_code})")
    
    def _on_sensor_change(self, kit, sensor_index, sensor_value):
        """Called when a sensor value changes"""
        self.logger.debug(f"Sensor {sensor_index} value changed to {sensor_value}")
        
        # Check if this sensor has VALUE_CHANGED callback type
        for sensor_info in self.sensor_infos:
            if (sensor_info.index == sensor_index and 
                sensor_info.callback_type == PhidgetSensorAgent.SensorInfo.CallbackType.VALUE_CHANGED):
                self.value_changed(sensor_index, sensor_value)
    
    def set_up(self):
        """Set up the agent"""
        super().set_up()
        
        # Initialize the Phidget interface kit
        self._init_phidget_interface_kit(self.interface_kit_serial)
        
        # Set up periodic reading for sensors with PERIODIC_READ callback type
        for sensor_info in self.sensor_infos:
            if sensor_info.callback_type == PhidgetSensorAgent.SensorInfo.CallbackType.PERIODIC_READ:
                self._setup_periodic_read(sensor_info)
    
    def _setup_periodic_read(self, sensor_info):
        """Set up periodic reading for a sensor"""
        def read_sensor():
            try:
                while self.is_attached:
                    if self.interface_kit and self.interface_kit.getAttached():
                        # Read the actual sensor value from hardware
                        value = self.interface_kit.getSensorValue(sensor_info.index)
                        self.periodic_read(sensor_info.index, value)
                    
                    # Sleep for the specified interval
                    time.sleep(sensor_info.interval / 1000.0)
            except PhidgetException as e:
                self.logger.error(f"Error in periodic sensor read: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error in periodic read: {e}")
        
        # Start the periodic read thread
        task = self.periodic_read_executor.submit(read_sensor)
        self.periodic_tasks.append(task)
    
    def run(self):
        """Main agent loop"""
        self.logger.info("PhidgetSensorAgent started")
        
        try:
            # Keep the agent running
            while True:
                time.sleep(1)
        except Exception as e:
            self.logger.error(f"Error in PhidgetSensorAgent loop: {e}")
    
    def get_sensor_value(self, sensor_index: int) -> int:
        """Get the current value of a sensor from the hardware"""
        try:
            if self.interface_kit and self.interface_kit.getAttached():
                return self.interface_kit.getSensorValue(sensor_index)
            return 0
        except PhidgetException as e:
            self.logger.error(f"Error getting sensor value: {e}")
            return 0
    
    def periodic_read(self, sensor_index: int, sensor_value: int):
        """
        Called periodically for sensors with PERIODIC_READ callback type
        Subclasses may override this method
        """
        pass
    
    def value_changed(self, sensor_index: int, sensor_value: int):
        """
        Called when a sensor value changes for sensors with VALUE_CHANGED callback type
        Subclasses must override this method
        """
        pass
    
    def terminate(self):
        """Clean up resources"""
        super().terminate()
        
        # Shutdown the periodic read executor
        self.periodic_read_executor.shutdown(wait=False)
        
        # Close the InterfaceKit connection
        try:
            if self.interface_kit and self.interface_kit.getAttached():
                self.interface_kit.close()
                self.logger.info("InterfaceKit closed")
        except PhidgetException as e:
            self.logger.error(f"Error closing InterfaceKit: {e}")