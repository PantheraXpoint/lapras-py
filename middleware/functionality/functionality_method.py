import functools
from typing import Callable, Optional, Any, Dict

class FunctionalityMethod:
    """
    A decorator for functionality methods in agent components.
    In Java, this was an annotation.
    """
    def __init__(self, name: str = "", description: str = ""):
        self.name = name
        self.description = description
        self.func = None
    
    def __call__(self, func):
        self.func = func
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Store metadata on the function
        wrapper.functionality_name = self.name or func.__name__
        wrapper.functionality_description = self.description
        wrapper.is_functionality_method = True
        
        return wrapper
    
    @staticmethod
    def get_functionality_name(method: Callable) -> str:
        """Get the functionality name from a method"""
        if hasattr(method, 'functionality_name'):
            return method.functionality_name
        return method.__name__
