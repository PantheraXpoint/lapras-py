from enum import Enum

class EventType(Enum):
    SUBSCRIBE_TOPIC_REQUESTED = "subscribe_topic_requested"
    PUBLISH_MESSAGE_REQUESTED = "publish_message_requested"
    MESSAGE_ARRIVED = "message_arrived"
    CONTEXT_UPDATED = "context_updated"
    ACTION_TAKEN = "action_taken"
    TASK_NOTIFIED = "task_notified"  # Deprecated?
    TASK_INITIATED = "task_initiated"
    TASK_TERMINATED = "task_terminated"
    USER_NOTIFIED = "user_notified"