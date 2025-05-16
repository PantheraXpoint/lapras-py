from lapras_middleware.agent import AgentComponent
from lapras_middleware.event import Event
import logging
import time
from typing import List, Optional
from dataclasses import dataclass
import concurrent.futures
from enum import Enum

logger = logging.getLogger(__name__)

class CallbackType(Enum):
    PERIODIC_READ = "PERIODIC_READ"
    VALUE_CHANGED = "VALUE_CHANGED"

@dataclass
class SensorInfo:
    index: int
    callback_type: CallbackType
    interval: Optional[int] = None

    def __post_init__(self):
        if self.callback_type == CallbackType.PERIODIC_READ and self.interval is None:
            raise ValueError("Sensors with PERIODIC_READ type must have an interval")
        if self.callback_type != CallbackType.PERIODIC_READ and self.interval is not None:
            raise ValueError("Only PERIODIC_READ sensors can have an interval")

class PhidgetSensorAgent(AgentComponent):
    ATTACHMENT_TIMEOUT = 2000  # milliseconds

    def __init__(self, event_dispatcher, agent):
        super().__init__(event_dispatcher, agent)
        
        # Get Phidget configuration from agent config
        self.interface_kit_serial = int(agent.agent_config.get_option("phidget_serial", "-1"))
        
        # Parse sensor configurations
        sensor_indices = agent.agent_config.get_option_as_array("phidget_sensor.index")
        sensor_callbacks = agent.agent_config.get_option_as_array("phidget_sensor.callback")
        intervals = agent.agent_config.get_option_as_array("phidget_sensor.interval")

        # Initialize sensor info list
        self.sensor_infos: List[SensorInfo] = []
        interval_index = 0
        
        for i in range(len(sensor_indices)):
            sensor_index = int(sensor_indices[i])
            callback_type = CallbackType[sensor_callbacks[i]]
            
            if callback_type == CallbackType.PERIODIC_READ:
                interval = int(intervals[interval_index])
                interval_index += 1
                self.sensor_infos.append(SensorInfo(sensor_index, callback_type, interval))
            else:
                self.sensor_infos.append(SensorInfo(sensor_index, callback_type))

        # Initialize executor for periodic readings
        self.periodic_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.periodic_futures = []
        
        # Placeholder for Phidget interface - to be initialized by specific implementations
        self.interface_kit = None

    def init_phidget_interface_kit(self):
        """
        This method should be implemented by specific Phidget library implementations.
        It should initialize the interface kit with the proper serial number.
        """
        raise NotImplementedError("Subclasses must implement init_phidget_interface_kit")

    def set_up(self):
        """Initialize the Phidget interface and set up periodic readings."""
        super().set_up()
        
        # Initialize the Phidget interface
        self.init_phidget_interface_kit()
        
        # Set up periodic readings
        for sensor_info in self.sensor_infos:
            if sensor_info.callback_type == CallbackType.PERIODIC_READ:
                future = self.periodic_executor.submit(
                    self._periodic_read_task,
                    sensor_info.index,
                    sensor_info.interval
                )
                self.periodic_futures.append(future)

    def _periodic_read_task(self, sensor_index: int, interval: int):
        """Task for periodic sensor reading."""
        while True:
            try:
                value = self.get_sensor_value(sensor_index)
                self.periodic_read(sensor_index, value)
                time.sleep(interval / 1000)  # Convert to seconds
            except Exception as e:
                logger.error(f"Error reading sensor {sensor_index}: {e}")

    def get_sensor_value(self, sensor_index: int) -> int:
        """
        This method should be implemented by specific Phidget library implementations.
        It should return the current value of the sensor at the given index.
        """
        raise NotImplementedError("Subclasses must implement get_sensor_value")

    def sensor_changed(self, sensor_index: int, value: int):
        """Handle sensor change events."""
        for sensor_info in self.sensor_infos:
            if sensor_info.index == sensor_index:
                if sensor_info.callback_type == CallbackType.VALUE_CHANGED:
                    self.value_changed(sensor_index, value)
                return

    def periodic_read(self, sensor_index: int, sensor_value: int):
        """Handle periodic sensor readings. Subclasses may override this method."""
        pass

    def value_changed(self, sensor_index: int, sensor_value: int):
        """Handle value change events. Subclasses may override this method."""
        pass

    def index_of(self, sensor_index: int) -> Optional[int]:
        """Get the list index of a sensor by its sensor index."""
        for i, sensor_info in enumerate(self.sensor_infos):
            if sensor_info.index == sensor_index:
                return i
        return None

    def stop(self):
        """Clean up resources."""
        # Cancel all periodic reading tasks
        for future in self.periodic_futures:
            future.cancel()
        
        # Shutdown the executor
        self.periodic_executor.shutdown(wait=False)
        
        super().stop() 