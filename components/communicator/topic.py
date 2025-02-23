from enum import Enum
from typing import Optional

class MessageType(Enum):
    CONTEXT = "context"
    FUNCTIONALITY = "functionality"
    ACTION = "action"
    TASK = "task"
    TASK_INITIATION = "task_initiation"
    TASK_TERMINATION = "task_termination"

class MqttTopic:
    MULTILEVEL_WILDCARD = "#"
    SINGLELEVEL_WILDCARD = "+"

class LaprasTopic:
    def __init__(self, place: Optional[str], message_type: MessageType, name: str):
        self.place = place
        self.message_type = message_type
        self.name = name