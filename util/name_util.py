# lapras/util/name_util.py
import re
from string import Template
from typing import Dict, Optional

from agent.agent_config import AgentConfig

class NameUtil:
    """
    Utility class for name expansion using templates.
    This is equivalent to the Java NameUtil class.
    """
    
    @staticmethod
    def expand(name: str, config: AgentConfig) -> str:
        """
        Expand variables in a template string using values from agent config.
        
        Args:
            name: The template string with placeholders in the format #{variable_name}
            config: The agent configuration containing variable values
            
        Returns:
            The expanded string with all variables replaced by their values
        """
        if not name:
            return ""
            
        # Find all variables in the template
        pattern = r'#\{([^}]+)\}'
        matches = re.finditer(pattern, name)
        
        # Create substitution map
        substitution_map = {}
        for match in matches:
            variable_name = match.group(1)
            value = config.get_option_or_default(variable_name, "")
            substitution_map[variable_name] = value
        
        # Replace variables with their values
        # We'll create a custom template class to handle our specific format
        class CustomTemplate(Template):
            delimiter = '#'
            pattern = r'\{([^}]*)\}'
            
        template = CustomTemplate(name)
        return template.safe_substitute(substitution_map)