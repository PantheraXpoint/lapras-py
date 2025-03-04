from enum import Enum, auto

class LoggerPrintMode(Enum):
    """
    Enum defining the logging levels for the custom logger.
    """
    INFO = auto()
    DEBUG = auto()
    ERROR = auto()
