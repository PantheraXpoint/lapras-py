import logging
from typing import Dict, List, Set
from dataclasses import dataclass
from datetime import datetime
import time
from lapras_middleware.agent import AgentComponent
from lapras_middleware.context import Context, ContextField
from lapras_middleware.event import Event, EventDispatcher

logger = logging.getLogger(__name__)

class MonnitServerAgent(AgentComponent):
    """
    MonnitServerAgent handles all sensors developed by Monnit.
    Currently handles seat occupancy sensor, IR motion sensor, and door sensor.
    """
    
    def __init__(self, event_dispatcher: EventDispatcher, agent):
        super().__init__(event_dispatcher, agent)
        
        # Initialize maps for different sensor types
        self.seat_serial_map: Dict[int, str] = {}
        self.motion_serial_map: Dict[int, str] = {}
        self.door_serial_map: Dict[int, str] = {}
        self.tilt_serial_map: Dict[int, str] = {}
        
        # Map for total seat count
        self.seat_count_map: Dict[str, bool] = {}
        
        # Lists for different sensor types
        self.seat_sensors: List = []
        self.motion_sensors: List = []
        self.door_sensors: List = []
        self.tilt_sensors: List = []
        
        # Get configuration
        self.agent_config = agent.agent_config
        self.context_manager = agent.context_manager
        
        # Initialize sensors from config
        self._initialize_seat_count()
        self._initialize_sensors()
        
    def _initialize_seat_count(self):
        """Initialize seat count from configuration"""
        seat_sensor_names = self.agent_config.get_option_as_array("seat_sensor_names")
        
        for seat_name in seat_sensor_names:
            self.seat_count_map[seat_name] = False
            
        self.context_manager.update_context("totalSeatCount", 0, self.agent_name)
        self.context_manager.set_publish_as_updated("totalSeatCount")
        
    def _initialize_sensors(self):
        """Initialize all sensor types from configuration"""
        # Initialize seat sensors
        seat_sensor_ids = self.agent_config.get_option_as_array("seat_sensor_ids")
        seat_sensor_names = self.agent_config.get_option_as_array("seat_sensor_names")
        self._init_sensor_type(seat_sensor_ids, seat_sensor_names, 
                             self.seat_sensors, self.seat_serial_map, "Seat_Occupancy")
        
        # Initialize motion sensors
        motion_sensor_ids = self.agent_config.get_option_as_array("motion_sensor_ids")
        motion_sensor_names = self.agent_config.get_option_as_array("motion_sensor_names")
        self._init_sensor_type(motion_sensor_ids, motion_sensor_names,
                             self.motion_sensors, self.motion_serial_map, "Infared_Motion")
        
        # Initialize door sensors
        door_sensor_ids = self.agent_config.get_option_as_array("door_sensor_ids")
        door_sensor_names = self.agent_config.get_option_as_array("door_sensor_names")
        self._init_sensor_type(door_sensor_ids, door_sensor_names,
                             self.door_sensors, self.door_serial_map, "Open_Closed")
        
        # Initialize tilt sensors
        tilt_sensor_ids = self.agent_config.get_option_as_array("tilt_sensor_ids")
        tilt_sensor_names = self.agent_config.get_option_as_array("tilt_sensor_names")
        self._init_sensor_type(tilt_sensor_ids, tilt_sensor_names,
                             self.tilt_sensors, self.tilt_serial_map, "Accelerometer_Tilt")
                             
    def _init_sensor_type(self, sensor_ids: List[str], sensor_names: List[str],
                         sensors: List, serial_map: Dict[int, str], sensor_type: str):
        """Initialize a specific type of sensor"""
        for idx, sensor_id in enumerate(sensor_ids):
            try:
                sensor_id_num = int(sensor_id)
                # Create sensor object (implementation depends on actual sensor class)
                sensor = self._create_sensor(sensor_id_num, sensor_type)
                sensors.append(sensor)
                serial_map[sensor_id_num] = sensor_names[idx]
                
                # Initialize context
                self.context_manager.update_context(sensor_names[idx], False, self.agent_name)
                
                # Handle tilt sensors specially
                if "tilt" in sensor_names[idx].lower():
                    self.context_manager.set_publish_as_updated(f"{sensor_names[idx]}_Pitch")
                    self.context_manager.set_publish_as_updated(f"{sensor_names[idx]}_Roll")
                else:
                    self.context_manager.set_publish_as_updated(sensor_names[idx])
                    
            except Exception as e:
                logger.error(f"Error initializing sensor {sensor_id}: {e}")
                
    def _create_sensor(self, sensor_id: int, sensor_type: str):
        """Create a sensor object based on type"""
        # This is a placeholder - actual implementation would depend on sensor hardware
        return {
            'id': sensor_id,
            'type': sensor_type,
            'version': '2.5.4.0',
            'generation': 'Commercial'
        }
        
    def set_up(self):
        """Set up the Monnit server and register sensors"""
        super().set_up()
        
        try:
            # Get configuration
            protocol = "TCP"
            port = int(self.agent_config.get_option("mineserver_port"))
            gateway_id = int(self.agent_config.get_option("gateway_id"))
            ip_addr = self.agent_config.get_option("mineserver_ip")
            
            # Initialize server
            self._init_server(protocol, ip_addr, port, gateway_id)
            
        except Exception as e:
            logger.error(f"Error setting up Monnit server: {e}")
            
    def _init_server(self, protocol: str, ip_addr: str, port: int, gateway_id: int):
        """Initialize the Monnit server"""
        # This is a placeholder - actual implementation would depend on Monnit API
        logger.info("Initializing Monnit server")
        # Here you would:
        # 1. Create server connection
        # 2. Register gateway
        # 3. Register sensors
        # 4. Set up message handlers
        
    def run(self):
        """Main run loop"""
        while True:
            try:
                time.sleep(1)
            except InterruptedException as e:
                logger.debug("Stopping server!")
                self._stop_server()
                break
                
    def _stop_server(self):
        """Stop the Monnit server"""
        try:
            # Actual server shutdown implementation would go here
            logger.info("Server stopped")
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            
    def handle_sensor_message(self, message: dict):
        """Handle incoming sensor messages"""
        try:
            sensor_id = message.get('sensor_id')
            state = message.get('state')
            timestamp = message.get('timestamp', int(time.time() * 1000))
            
            if sensor_id in self.seat_serial_map:
                self._handle_seat_sensor_message(sensor_id, state, timestamp)
            elif sensor_id in self.motion_serial_map:
                self._handle_motion_sensor_message(sensor_id, state, timestamp)
            elif sensor_id in self.door_serial_map:
                self._handle_door_sensor_message(sensor_id, state, timestamp)
            elif sensor_id in self.tilt_serial_map:
                self._handle_tilt_sensor_message(sensor_id, state, timestamp)
            else:
                logger.info("Sensor is not registered")
                
        except Exception as e:
            logger.error(f"Error handling sensor message: {e}")
            
    def _handle_seat_sensor_message(self, sensor_id: int, state: int, timestamp: int):
        """Handle seat sensor messages"""
        context_name = self.seat_serial_map.get(sensor_id)
        if context_name:
            logger.info(f"{context_name} updated")
            is_occupied = (state == 2)
            self.context_manager.update_context(context_name, is_occupied, self.agent_name, timestamp)
            self.seat_count_map[context_name] = is_occupied
            
            # Update total seat count
            total_occupied = sum(1 for occupied in self.seat_count_map.values() if occupied)
            self.context_manager.update_context("totalSeatCount", total_occupied, self.agent_name, timestamp)
            
    def _handle_motion_sensor_message(self, sensor_id: int, state: int, timestamp: int):
        """Handle motion sensor messages"""
        context_name = self.motion_serial_map.get(sensor_id)
        if context_name:
            logger.info(f"{context_name} updated")
            self.context_manager.update_context(context_name, state == 2, self.agent_name, timestamp)
            
    def _handle_door_sensor_message(self, sensor_id: int, state: int, timestamp: int):
        """Handle door sensor messages"""
        context_name = self.door_serial_map.get(sensor_id)
        if context_name:
            logger.info(f"{context_name} updated")
            self.context_manager.update_context(context_name, state == 2, self.agent_name, timestamp)
            
    def _handle_tilt_sensor_message(self, sensor_id: int, state: int, timestamp: int):
        """Handle tilt sensor messages"""
        context_name = self.tilt_serial_map.get(sensor_id)
        if context_name:
            logger.info(f"{context_name} updated")
            # Implementation would depend on tilt sensor data format
            # You might need to handle pitch and roll separately 