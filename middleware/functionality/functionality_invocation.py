import re
import time
import json
from typing import List, Dict, Any, Optional, ClassVar, Type, Tuple

from communicator.lapras_message import LaprasMessage
from communicator.message_type import MessageType
from communicator.message_qos import MessageQos

class FunctionalityInvocation(LaprasMessage):
    """Represents an invocation of a functionality method"""
    
    def __init__(self, name: Optional[str] = None, arguments: Optional[List[Any]] = None, 
                 timestamp: Optional[int] = None, publisher: Optional[str] = None):
        super().__init__(name, timestamp, publisher)
        self.arguments = arguments or []
        self.by_user = False
    
    def __str__(self) -> str:
        """String representation of the invocation"""
        arg_strings = []
        for arg in self.arguments:
            if isinstance(arg, (bool, int, float)):
                arg_strings.append(str(arg))
            elif isinstance(arg, str):
                arg_strings.append(f"{arg}")
            else:
                arg_strings.append(str(arg))
        
        return f"{self.name}({', '.join(arg_strings)})"
    
    @classmethod
    def from_string(cls, string: str, timestamp: Optional[int] = None, 
                   publisher: Optional[str] = None) -> 'FunctionalityInvocation':
        """Create a functionality invocation from a string representation"""
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        
        # Parse the functionality name and arguments
        pattern = r"([a-z_A-Z]\w+)\(((?:\s*[^ \t\n\x0b\r\f,]+\s*)?|(?:\s*[^ \t\n\x0b\r\f,]+\s*)(?:,(?:\s*[^ \t\n\x0b\r\f,]+\s*))*))"
        match = re.match(pattern, string)
        if not match:
            raise ValueError("Failed to parse functionality")
        
        functionality_name = match.group(1)
        
        # Parse the arguments
        arguments = []
        if match.group(2):
            arg_strings = [arg.strip() for arg in match.group(2).split(',')]
            
            for arg in arg_strings:
                if not arg:
                    continue
                
                # Parse different types of arguments
                if arg.lower() == "true":
                    arguments.append(True)
                elif arg.lower() == "false":
                    arguments.append(False)
                elif arg.startswith('"') and arg.endswith('"'):
                    arguments.append(arg[1:-1])
                elif re.match(r"\d+$", arg):
                    arguments.append(int(arg))
                elif re.match(r"\d*\.\d+$", arg):
                    arguments.append(float(arg))
                else:
                    raise ValueError(f"Failed to parse argument: {arg}")
        
        return cls(functionality_name, arguments, timestamp, publisher)
    
    @classmethod
    def from_payload(cls, payload: bytes) -> Optional['FunctionalityInvocation']:
        """Create a functionality invocation from a payload"""
        return LaprasMessage.from_payload(payload)
    
    def get_name(self) -> str:
        """Get the name of the functionality"""
        return self.name
    
    def set_name(self, name: str):
        """Set the name of the functionality"""
        self.name = name
    
    def get_arguments(self) -> List[Any]:
        """Get the arguments for the functionality"""
        return self.arguments
    
    def set_arguments(self, arguments: List[Any]):
        """Set the arguments for the functionality"""
        self.arguments = arguments
    
    def is_by_user(self) -> bool:
        """Check if the invocation was triggered by a user"""
        return self.by_user
    
    def set_by_user(self, by_user: bool):
        """Set whether the invocation was triggered by a user"""
        self.by_user = by_user
    
    def get_type(self) -> MessageType:
        """Get the message type"""
        return MessageType.FUNCTIONALITY
    
    def get_qos(self) -> MessageQos:
        """Get the message QoS"""
        return MessageQos.EXACTLY_ONCE
    
    def get_retained(self) -> bool:
        """Get whether the message should be retained"""
        return False
