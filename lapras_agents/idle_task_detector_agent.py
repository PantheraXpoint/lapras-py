import logging
import time
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from .agent import AgentComponent

logger = logging.getLogger(__name__)

@dataclass
class TaskNotification:
    task_type: str
    timestamp: int
    agent_name: str
    involved_agents: List[str]

class IdleTaskDetectorAgent(AgentComponent):
    PRESENCE_CHECK_INTERVAL = 60  # 1 minute in seconds
    
    def __init__(self, event_dispatcher, agent):
        super().__init__(event_dispatcher, agent)
        self.presence_history: List[str] = []
        self.current_presence: Optional[str] = None
        self.inferred_user_presence = None  # This would be set by the context system
        
    def subscribe_events(self):
        self.subscribe_event("CONTEXT_UPDATED")
        self.subscribe_event("TASK_NOTIFIED")  # For testing
        
    def handle_event(self, event) -> bool:
        if event.type == "CONTEXT_UPDATED":
            context = event.data
            if context.name == "InferredUserPresence":
                self.current_presence = context.value
                logger.info(f"Current presence: {self.current_presence}")
        return True
        
    def run(self):
        while True:
            if self.current_presence is not None:
                self.presence_history.append(self.current_presence)
                
            history_length = len(self.presence_history)
            
            if history_length > 10 and self.current_presence == "present":
                last_presence = self.presence_history[-10:]
                
                if all(p == "present" for p in last_presence):
                    self.notify_task_idle()
                    
            if history_length > 1000:
                self.presence_history.clear()
                
            time.sleep(self.PRESENCE_CHECK_INTERVAL)
            
    def notify_task_idle(self):
        logger.info(f"Presence history: {self.presence_history}")
        logger.info("Current task is Idle")
        
        timestamp = int(datetime.now().timestamp() * 1000)
        involved_agents = self.agent.config.get_option_as_array("involved_agents")
        
        task_notification = TaskNotification(
            task_type="Idle",
            timestamp=timestamp,
            agent_name=self.agent.config.agent_name,
            involved_agents=involved_agents
        )
        
        # This would be implemented based on your MQTT system
        # self.mqtt_communicator.publish(topic, task_notification) 