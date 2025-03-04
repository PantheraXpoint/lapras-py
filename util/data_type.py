# lapras/util/data_type.py
from enum import Enum
import os
import pathlib
from typing import Any

class DataType(Enum):
    """
    Enumeration of data types supported by the LAPRAS functionality system.
    """
    INTEGER = "integer"
    LONG = "long"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    FILE = "file"
    
    @staticmethod
    def get_class(data_type):
        """Get the Python class for a given DataType"""
        type_map = {
            DataType.INTEGER: int,
            DataType.LONG: int,  # Python doesn't distinguish between int and long
            DataType.FLOAT: float,
            DataType.STRING: str,
            DataType.BOOLEAN: bool,
            DataType.FILE: pathlib.Path  # Using pathlib.Path instead of string for files
        }
        if data_type in type_map:
            return type_map[data_type]
        raise ValueError(f"Unknown data type: {data_type}")
    
    @staticmethod
    def from_class(cls):
        """Get the DataType for a given Python class"""
        if cls == int:
            return DataType.INTEGER
        elif cls == float:
            return DataType.FLOAT
        elif cls == str:
            return DataType.STRING
        elif cls == bool:
            return DataType.BOOLEAN
        elif cls == pathlib.Path or cls == os.PathLike:
            return DataType.FILE
        raise ValueError(f"No corresponding DataType for class: {cls.__name__}")
    
    @staticmethod
    def convert_value(value: Any, target_type: 'DataType') -> Any:
        """
        Convert a value to the specified data type.
        
        Args:
            value: The value to convert
            target_type: The target data type
            
        Returns:
            The converted value
            
        Raises:
            ValueError: If the conversion is not possible
        """
        if value is None:
            return None
            
        try:
            if target_type == DataType.INTEGER:
                return int(value)
            elif target_type == DataType.LONG:
                return int(value)
            elif target_type == DataType.FLOAT:
                return float(value)
            elif target_type == DataType.STRING:
                return str(value)
            elif target_type == DataType.BOOLEAN:
                if isinstance(value, str):
                    return value.lower() in ('true', 'yes', '1', 'y')
                return bool(value)
            elif target_type == DataType.FILE:
                return str(value)
            
            raise ValueError(f"Cannot convert to {target_type}")
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert {value} to {target_type}: {e}")
