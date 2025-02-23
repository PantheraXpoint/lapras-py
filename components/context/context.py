from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class Context:
    """Represents a context in the LAPRAS system."""
    name: str
    value: Any
    timestamp: int
    publisher: Optional[str] = None