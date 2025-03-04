from typing import Any, Optional, Type, Callable
import functools

class ContextField:
    """
    A decorator to mark fields in an agent component as context fields.
    We use this as a descriptor to maintain similar behavior.
    """
    
    def __init__(self, name: str = "", publish_as_updated: bool = False, publish_interval: int = 0):
        self.name = name
        self.publish_as_updated = publish_as_updated
        self.publish_interval = publish_interval
        self.value = None
        
    def __get__(self, obj, objtype=None):
        return self.value
    
    def __set__(self, obj, value):
        self.value = value
        
        # If the object has a context_manager, update the context
        if hasattr(obj, 'context_manager') and self.name:
            obj.context_manager.update_context(self.name, value, obj.agent_name)