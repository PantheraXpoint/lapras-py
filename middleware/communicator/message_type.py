from enum import Enum

class MessageType(Enum):
    CONTEXT = "context"
    FUNCTIONALITY = "functionality"
    ACTION = "action"
    TASK = "task"
    USER = "user"
    TASK_INITIATION = "task_initiation"
    TASK_TERMINATION = "task_termination"
    
    def __str__(self):
        return self.value
    
    @classmethod
    def from_string(cls, value):
        for m in cls:
            if m.value == value:
                return m
        raise ValueError(f"No such enum constant with specified value: {value}")
