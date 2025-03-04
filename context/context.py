from typing import Optional, Any
from context.context_instance import ContextInstance

class Context:
    def __init__(self, name: str, instance: Optional[ContextInstance], agent_component):
        self.name = name
        self.instance = instance
        self.initial_value = None
        self.agent_component = agent_component
    
    def get_name(self) -> str:
        return self.name
    
    def set_name(self, name: str):
        self.name = name
    
    def get_instance(self) -> Optional[ContextInstance]:
        return self.instance
    
    def set_instance(self, instance: ContextInstance):
        self.instance = instance
    
    def set_initial_value(self, initial_value: Any):
        self.initial_value = initial_value
    
    def get_value(self) -> Any:
        return self.initial_value if self.instance is None else self.instance.get_value()
    
    def update_value(self, value: Any):
        self.agent_component.context_manager.update_context(
            self.name, value, self.agent_component.agent_name
        )
    
    def get_value_type(self) -> Optional[type]:
        return None if self.instance is None else self.instance.get_value_type()
