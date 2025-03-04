import logging
import base64
import tempfile
import os
import threading
from typing import Dict, List, Callable, Any, Optional
import concurrent.futures
import time

from agent.component import Component
from event.event import Event
from event.event_type import EventType
from event.event_dispatcher import EventDispatcher
from communicator.lapras_topic import LaprasTopic
from communicator.message_type import MessageType
from communicator.mqtt_communicator import MqttCommunicator
from functionality.functionality_invocation import FunctionalityInvocation
from functionality.functionality_signature import FunctionalitySignature
from util.data_type import DataType


class FunctionalityExecutor(Component):
    """
    Executes functionality methods that are registered with the system.
    Handles incoming functionality requests via MQTT and manages their execution.
    """
    
    def __init__(self, event_dispatcher: EventDispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Executor for running functionalities
        self.functionality_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        # Maps for storing functionality handlers and signatures
        self.functionality_function_map: Dict[str, Callable] = {}
        self.functionality_signature_map: Dict[str, FunctionalitySignature] = {}
        
        # Get MQTT communicator and agent name from agent
        self.mqtt_communicator = agent.get_mqtt_communicator()
        self.agent_name = agent.get_agent_config().get_agent_name()
    
    def subscribe_events(self):
        """Subscribe to relevant events"""
        self.subscribe_event(EventType.MESSAGE_ARRIVED)
    
    def handle_event(self, event: Event) -> bool:
        """Handle incoming events"""
        if event.get_type() == EventType.MESSAGE_ARRIVED:
            data = event.get_data()
            topic: LaprasTopic = data[0]
            payload: bytes = data[1]
            
            # Check if this is a functionality message
            if topic.get_message_type() != MessageType.FUNCTIONALITY:
                return True
            
            # Parse the functionality invocation
            functionality_invocation = FunctionalityInvocation.from_payload(payload)
            if not functionality_invocation:
                return True
            
            # Invoke the functionality
            self.invoke_functionality(functionality_invocation)
            return True
        
        return False
    
    def get_functionality_signature(self, functionality_name: str) -> Optional[FunctionalitySignature]:
        """Get the signature for a functionality"""
        return self.functionality_signature_map.get(functionality_name)
    
    def list_functionality_signatures(self) -> List[FunctionalitySignature]:
        """List all registered functionality signatures"""
        return list(self.functionality_signature_map.values())
    
    def register_functionality(self, functionality_name: str, function: Callable, signature: Optional[FunctionalitySignature] = None):
        """Register a functionality with the system"""
        self.functionality_function_map[functionality_name] = function
        
        if not signature:
            # Create a minimal signature if none provided
            signature = FunctionalitySignature(functionality_name, [], "")
        
        self.functionality_signature_map[functionality_name] = signature
        
        self.logger.debug(f"Functionality {functionality_name} has been registered")
        
        # Subscribe to MQTT topic for this functionality
        topic = LaprasTopic(None, MessageType.FUNCTIONALITY, functionality_name)
        self.mqtt_communicator.subscribe_topic(topic)
    
    def register_method_functionality(self, functionality_name: str, method, instance):
        """Register a method as a functionality"""
        # Get signature from method
        signature = FunctionalitySignature.from_method_with_name(functionality_name, method)
        
        # Create function that invokes the method
        def invoke_method(arguments):
            try:
                return method(instance, *arguments)
            except Exception as e:
                self.logger.error(f"Error executing functionality {functionality_name}: {e}")
                return None
        
        # Register the functionality
        self.register_functionality(functionality_name, invoke_method, signature)
    
    def invoke_functionality(self, functionality_invocation: FunctionalityInvocation):
        """Invoke a functionality locally"""
        functionality_name = functionality_invocation.get_name()
        function = self.functionality_function_map.get(functionality_name)
        
        if not function:
            self.logger.warning(f"No functionality registered with name: {functionality_name}")
            return
        
        # Process arguments according to signature
        signature = self.functionality_signature_map.get(functionality_name)
        arguments = self._process_arguments(functionality_invocation.get_arguments(), signature)
        
        # Submit the functionality for execution
        self.functionality_executor.submit(self._execute_functionality, functionality_name, function, arguments)
    
    def invoke_functionality_by_name(self, functionality_name: str, arguments: List[Any]):
        """Invoke a functionality by name with the given arguments"""
        functionality_invocation = FunctionalityInvocation(
            functionality_name, 
            arguments, 
            int(time.time() * 1000), 
            self.agent_name
        )
        self.invoke_functionality(functionality_invocation)
    
    def invoke_remote_functionality(self, functionality_name: str, arguments: List[Any]):
        """Invoke a functionality on a remote agent via MQTT"""
        functionality_invocation = FunctionalityInvocation(
            functionality_name, 
            arguments, 
            int(time.time() * 1000), 
            self.agent_name
        )
        
        # Publish to MQTT
        topic = LaprasTopic(None, MessageType.FUNCTIONALITY, functionality_name)
        self.mqtt_communicator.publish(topic, functionality_invocation)
    
    def _execute_functionality(self, functionality_name: str, function: Callable, arguments: List[Any]):
        """Execute a functionality function with the given arguments"""
        self.logger.debug(f"Invoking functionality {functionality_name}")
        try:
            function(arguments)
        except Exception as e:
            self.logger.error(f"Error executing functionality {functionality_name}: {e}")
    
    def _process_arguments(self, arguments: List[Any], signature: FunctionalitySignature) -> List[Any]:
        """Process and validate arguments against a functionality signature"""
        if arguments is None:
            if signature and len(signature.get_parameters()) > 0:
                raise ValueError("Arguments expected but none provided")
            return []
        
        if signature and len(arguments) != len(signature.get_parameters()):
            raise ValueError(f"Expected {len(signature.get_parameters())} arguments, got {len(arguments)}")
        
        # If no signature or no parameters, return arguments as is
        if not signature or not signature.get_parameters():
            return arguments
        
        result = []
        for i, param_sig in enumerate(signature.get_parameters()):
            if param_sig.get_type() == DataType.FILE:
                # Handle file type: decode base64 and save to temp file
                try:
                    file_base64 = str(arguments[i]).replace('\n', '')
                    file_bytes = base64.b64decode(file_base64)
                    
                    # Create temp file
                    fd, path = tempfile.mkstemp(prefix="lapras_")
                    with os.fdopen(fd, 'wb') as tmp:
                        tmp.write(file_bytes)
                    
                    result.append(path)
                except Exception as e:
                    self.logger.error(f"Error processing file argument: {e}")
                    result.append(None)
            else:
                # Pass other arguments through directly
                result.append(arguments[i])
        
        return result