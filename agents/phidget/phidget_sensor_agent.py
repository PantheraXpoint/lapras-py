import logging
import threading
import time
from enum import Enum
from typing import List, Dict, Optional, Any
import concurrent.futures

from agent.agent_component import AgentComponent

class PhidgetSensorAgent(AgentComponent):
    """
    Base class for Phidget sensor agents.
    simplified implementation that simulates Phidget sensors.
    integrate with actual Phidget hardware.
    """
    
    class SensorInfo:
        """Information about connected sensors"""
        
        class CallbackType(Enum):
            PERIODIC_READ = "PERIODIC_READ"
            VALUE_CHANGED = "VALUE_CHANGED"
        
        def __init__(self, index: int, callback_type: 'PhidgetSensorAgent.SensorInfo.CallbackType', 
                     interval: Optional[int] = None):
            """
            Initialize a SensorInfo object
            
            Args:
                index: Sensor index
                callback_type: Type of callback to use for this sensor
                interval: Interval in milliseconds (required for PERIODIC_READ)
            """
            if callback_type == PhidgetSensorAgent.SensorInfo.CallbackType.PERIODIC_READ and interval is None:
                raise ValueError("Sensors with PERIODIC_READ type of callback should include an interval")
                
            if callback_type != PhidgetSensorAgent.SensorInfo.CallbackType.PERIODIC_READ and interval is not None:
                raise ValueError("Interval should only be specified for PERIODIC_READ sensors")
                
            self.index = index
            self.callback_type = callback_type
            self.interval = interval
    
    def __init__(self, event_dispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Get configuration from agent
        self.interface_kit_serial = int(
            agent.get_agent_config().get_option_or_default("phidget_serial", "-1")
        )
        
        # Set up sensor info list
        self.sensor_infos: List[PhidgetSensorAgent.SensorInfo] = []
        
        # Parse sensor configuration from agent config
        self._parse_sensor_config(agent)
        
        # Simulated sensor values
        self.sensor_values: Dict[int, int] = {}
        
        # Thread pool for periodic reading
        self.periodic_read_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.periodic_tasks = []
        
        # Flag to indicate if the interface kit is attached
        self.is_attached = False
    
    def _parse_sensor_config(self, agent):
        """Parse sensor configuration from agent config"""
        try:
            # Get sensor indices, callback types, and intervals from config
            sensor_indices = agent.get_agent_config().get_option_as_array("phidget_sensor.index")
            sensor_callbacks = agent.get_agent_config().get_option_as_array("phidget_sensor.callback")
            intervals = agent.get_agent_config().get_option_as_array("phidget_sensor.interval")
            
            if not sensor_indices:
                # No sensors configured, use defaults for testing
                self.logger.warning("No sensors configured, using defaults for testing")
                sensor_indices = ["0"]
                sensor_callbacks = ["VALUE_CHANGED"]
                intervals = []
            
            interval_index = 0
            for i in range(len(sensor_indices)):
                sensor_index = int(sensor_indices[i])
                callback_type = PhidgetSensorAgent.SensorInfo.CallbackType[sensor_callbacks[i]]
                
                if callback_type == PhidgetSensorAgent.SensorInfo.CallbackType.PERIODIC_READ:
                    interval = int(intervals[interval_index])
                    interval_index += 1
                    sensor_info = PhidgetSensorAgent.SensorInfo(sensor_index, callback_type, interval)
                else:
                    sensor_info = PhidgetSensorAgent.SensorInfo(sensor_index, callback_type)
                
                self.sensor_infos.append(sensor_info)
                
        except Exception as e:
            self.logger.error(f"Error parsing sensor configuration: {e}")
            # Add a default sensor for testing
            self.sensor_infos.append(
                PhidgetSensorAgent.SensorInfo(
                    0, PhidgetSensorAgent.SensorInfo.CallbackType.VALUE_CHANGED
                )
            )
    
    def _init_phidget_interface_kit(self, serial: int):
        """Initialize the Phidget interface kit"""
        try:
            # In a real implementation, this would connect to actual hardware
            # For simulation, we just set the attached flag
            self.logger.info(f"Initializing Phidget interface kit with serial: {serial}")
            
            # Simulate attachment delay
            time.sleep(1)
            
            self.is_attached = True
            self.logger.info("Phidget interface kit attached")
            
            # Initialize sensor values
            for sensor_info in self.sensor_infos:
                self.sensor_values[sensor_info.index] = 0
                
        except Exception as e:
            self.logger.error(f"Error initializing Phidget interface kit: {e}")
    
    def set_up(self):
        """Set up the agent"""
        super().set_up()
        
        # Initialize the Phidget interface kit
        self._init_phidget_interface_kit(self.interface_kit_serial)
        
        # Set up periodic reading for sensors with PERIODIC_READ callback type
        for sensor_info in self.sensor_infos:
            if sensor_info.callback_type == PhidgetSensorAgent.SensorInfo.CallbackType.PERIODIC_READ:
                self._setup_periodic_read(sensor_info)
    
    def _setup_periodic_read(self, sensor_info: SensorInfo):
        """Set up periodic reading for a sensor"""
        def read_sensor():
            try:
                while self.is_attached:
                    # In a real implementation, this would read from actual hardware
                    # For simulation, we just use the current value
                    value = self.sensor_values.get(sensor_info.index, 0)
                    self.periodic_read(sensor_info.index, value)
                    
                    # Sleep for the specified interval
                    time.sleep(sensor_info.interval / 1000.0)
            except Exception as e:
                self.logger.error(f"Error in periodic sensor read: {e}")
        
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
                
                # In a real implementation, this would be done by the Phidget event system
                # For simulation, we'll check for value changes here
                self._check_for_value_changes()
                
        except Exception as e:
            self.logger.error(f"Error in PhidgetSensorAgent loop: {e}")
    
    def _check_for_value_changes(self):
        """Check for value changes in sensors with VALUE_CHANGED callback type"""
        # This is only needed for simulation
        # In a real implementation, the Phidget event system would call sensorChanged
        pass
    
    def get_sensor_value(self, sensor_index: int) -> int:
        """Get the current value of a sensor"""
        return self.sensor_values.get(sensor_index, 0)
    
    def set_sensor_value(self, sensor_index: int, value: int):
        """
        Set the value of a sensor - this is for simulation only
        In a real implementation, values would come from hardware
        """
        old_value = self.sensor_values.get(sensor_index, 0)
        self.sensor_values[sensor_index] = value
        
        # If the value has changed and the sensor has VALUE_CHANGED callback type,
        # call the valueChanged method
        if old_value != value:
            for sensor_info in self.sensor_infos:
                if (sensor_info.index == sensor_index and 
                    sensor_info.callback_type == PhidgetSensorAgent.SensorInfo.CallbackType.VALUE_CHANGED):
                    self.sensor_changed(sensor_index, value)
    
    def sensor_changed(self, sensor_index: int, value: int):
        """Called when a sensor value changes"""
        for sensor_info in self.sensor_infos:
            if sensor_info.index == sensor_index:
                if sensor_info.callback_type == PhidgetSensorAgent.SensorInfo.CallbackType.VALUE_CHANGED:
                    self.value_changed(sensor_index, value)
    
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
    
    def index_of(self, sensor_index: int) -> Optional[int]:
        """Get the index of a sensor in the sensor_infos list"""
        for i, sensor_info in enumerate(self.sensor_infos):
            if sensor_info.index == sensor_index:
                return i
        return None
    
    def terminate(self):
        """Terminate the agent"""
        super().terminate()
        
        # Clean up periodic read tasks
        self.periodic_read_executor.shutdown(wait=False)
        
        # In a real implementation, this would close the Phidget connection
        self.is_attached = False