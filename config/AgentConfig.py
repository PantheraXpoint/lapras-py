from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
from pathlib import Path
import io

@dataclass
class AgentConfig:
    agent_name: str
    place_name: str
    broker_address: str
    options: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_stream(cls, stream: io.IOBase) -> 'AgentConfig':
        """Create config from a file stream."""
        config_data = json.load(stream)
        return cls(
            agent_name=config_data.get('agent_name'),
            place_name=config_data.get('place_name'),
            broker_address=config_data.get('broker_address'),
            options=config_data.get('options', {})
        )

    def get_option(self, key: str) -> Optional[str]:
        """Get option value by key."""
        return self.options.get(key)

    def get_option_as_array(self, key: str) -> List[str]:
        """Get option value as string array."""
        value = self.get_option(key)
        return value.split(',') if value else []