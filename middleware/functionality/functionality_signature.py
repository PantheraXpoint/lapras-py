import inspect
from typing import List, Dict, Any, Callable, Optional, Type
from dataclasses import dataclass

from util.data_type import DataType
from functionality.functionality_method import FunctionalityMethod

@dataclass
class ParameterSignature:
    """Signature for a functionality parameter"""
    name: str
    type: DataType
    
    def __init__(self, name: str, type_: DataType):
        self.name = name
        self.type = type_

class FunctionalitySignature:
    """Signature for a functionality method"""
    
    def __init__(self, name: str, parameters: List[ParameterSignature], description: str):
        self.name = name
        self.parameters = parameters
        self.description = description
    
    @classmethod
    def from_method_with_name(cls, functionality_name: str, method: Callable) -> 'FunctionalitySignature':
        """Create a signature from a method with a specified name"""
        signature = cls.from_method(method)
        signature.name = functionality_name
        return signature
    
    @classmethod
    def from_method(cls, method: Callable) -> 'FunctionalitySignature':
        """Create a signature from a method"""
        # Get the method's signature using inspect
        sig = inspect.signature(method)
        
        # Get functionality metadata if available
        functionality_name = FunctionalityMethod.get_functionality_name(method)
        description = getattr(method, 'functionality_description', "")
        
        # Create parameter signatures
        parameters = []
        for param_name, param in sig.parameters.items():
            # Skip 'self' parameter
            if param_name == 'self':
                continue
                
            # Get parameter type (use Any as default if not specified)
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else Any
            data_type = DataType.from_class(param_type)
            
            parameters.append(ParameterSignature(param_name, data_type))
        
        return cls(functionality_name, parameters, description)
    
    @staticmethod
    def get_functionality_name(method: Callable) -> str:
        """Get the functionality name from a method"""
        return FunctionalityMethod.get_functionality_name(method)
    
    def get_name(self) -> str:
        """Get the name of this functionality"""
        return self.name
    
    def get_parameters(self) -> List[ParameterSignature]:
        """Get the parameters of this functionality"""
        return self.parameters
    
    def get_description(self) -> str:
        """Get the description of this functionality"""
        return self.description