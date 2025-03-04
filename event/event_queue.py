import queue
from event.event import Event

class EventQueue(queue.Queue):
    def __init__(self):
        super().__init__()
