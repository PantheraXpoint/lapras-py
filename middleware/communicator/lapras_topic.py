from typing import List, Optional
from communicator.mqtt_topic import MqttTopic
from communicator.message_type import MessageType

class LaprasTopic(MqttTopic):
    def __init__(self, place_name: Optional[str], message_type: Optional[MessageType], *subtopics):
        super().__init__()
        self.tokens = [None] * (2 + len(subtopics))
        self.set_place_name(place_name)
        self.set_message_type(message_type)
        self.set_subtopics(*subtopics)
    
    @classmethod
    def from_string(cls, topic_string: str) -> 'LaprasTopic':
        topic = cls(None, None)
        topic.tokens = topic_string.split("/")
        return topic
    
    def get_place_name(self) -> Optional[str]:
        return self.tokens[0]
    
    def set_place_name(self, place_name: Optional[str]):
        self.tokens[0] = place_name
    
    def get_message_type(self) -> Optional[MessageType]:
        if self.tokens[1] is None:
            return None
        return MessageType.from_string(self.tokens[1])
    
    def set_message_type(self, message_type: Optional[MessageType]):
        if message_type is None:
            self.tokens[1] = None
        else:
            self.tokens[1] = str(message_type)
    
    def get_subtopics(self) -> List[str]:
        return self.tokens[2:]
    
    def set_subtopics(self, *subtopics):
        for i, subtopic in enumerate(subtopics):
            if i < len(self.tokens) - 2:
                self.tokens[i + 2] = subtopic