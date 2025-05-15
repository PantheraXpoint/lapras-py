from typing import Optional
from .event import EventDispatcher
from .agent import Agent

class Component:
    """Base class for all components in the LAPRAS system."""
    
    def __init__(self, event_dispatcher: EventDispatcher, agent: Agent):
        """Initialize a component with an event dispatcher and agent reference."""
        self.event_dispatcher = event_dispatcher
        self.agent = agent
        
    def start(self) -> None:
        """Start the component. Override this method in subclasses."""
        pass
        
    def stop(self) -> None:
        """Stop the component. Override this method in subclasses."""
        pass
        
    def handle_event(self, event) -> bool:
        """Handle an event. Override this method in subclasses."""
        return True 