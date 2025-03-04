from abc import ABC

class MqttTopic(ABC):
    SINGLELEVEL_WILDCARD = "+"
    MULTILEVEL_WILDCARD = "#"
    DELIMITER = "/"
    
    def __init__(self, topic_string=None):
        if topic_string:
            self.tokens = topic_string.split("/")
        else:
            self.tokens = None
    
    def __str__(self):
        if not self.tokens:
            return ""
            
        result = []
        for token in self.tokens:
            if token is not None:
                result.append(token)
            else:
                result.append(self.SINGLELEVEL_WILDCARD)
        
        return self.DELIMITER.join(result)