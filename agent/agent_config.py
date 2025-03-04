import os
import configparser
from typing import Dict, List, Optional, Iterator

class AgentConfig:
    def __init__(self, agent_name: str = None):
        self.options = configparser.ConfigParser()
        self.options.add_section('DEFAULT')
        if agent_name:
            self.set_agent_name(agent_name)
    
    @classmethod
    def from_file(cls, path: str) -> 'AgentConfig':
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        
        config = cls()
        config.options.read(path)
        return config
    
    @classmethod
    def from_stream(cls, input_stream) -> 'AgentConfig':
        config = cls()
        config.options.read_file(input_stream)
        return config
    
    def get_agent_name(self) -> str:
        return self.get_option('agent_name')
    
    def set_agent_name(self, agent_name: str) -> 'AgentConfig':
        self.set_option('agent_name', agent_name)
        return self
    
    def get_broker_address(self) -> str:
        return self.get_option('broker_address')
    
    def set_broker_address(self, broker_address: str) -> 'AgentConfig':
        self.set_option('broker_address', broker_address)
        return self
    
    def get_place_name(self) -> str:
        return self.get_option('place_name')
    
    def set_place_name(self, place_name: str) -> 'AgentConfig':
        self.set_option('place_name', place_name)
        return self
    
    def get_option(self, option_name: str) -> Optional[str]:
        return self.options.get('DEFAULT', option_name, fallback=None)
    
    def get_option_or_default(self, option_name: str, default_value: str) -> str:
        return self.options.get('DEFAULT', option_name, fallback=default_value)
    
    def get_option_as_array(self, option_name: str) -> List[str]:
        value = self.get_option(option_name)
        if not value:
            return []
        return [item.strip() for item in value.split(',')]
    
    def set_option(self, option_name: str, option_value: str) -> 'AgentConfig':
        self.options.set('DEFAULT', option_name, option_value)
        return self
    
    def list_option_names(self) -> Iterator[str]:
        return self.options['DEFAULT'].keys()