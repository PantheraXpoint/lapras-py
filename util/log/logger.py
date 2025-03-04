import sys
from typing import List, Set, ClassVar
from util.log.logger_print_mode import LoggerPrintMode

class Logger:
    """
    A simple lightweight logger for LAPRAS.
    simpler alternative to full logging.
    """
    
    _instance = None
    _print_modes: Set[LoggerPrintMode] = {LoggerPrintMode.INFO, LoggerPrintMode.ERROR, LoggerPrintMode.DEBUG}  # default
    
    @classmethod
    def set_mode(cls, mode_conf: List[LoggerPrintMode]) -> None:
        """
        Set which logging levels should be displayed.
        
        Args:
            mode_conf: List of enabled logging levels
        """
        if not cls._instance:
            cls._instance = Logger()
        
        cls._print_modes = set(mode_conf)
    
    @classmethod
    def info(cls, log: str) -> None:
        """
        Log an info message if INFO level is enabled.
        
        Args:
            log: The message to log
        """
        if not cls._instance:
            cls._instance = Logger()
        
        if cls._allowed(LoggerPrintMode.INFO):
            print(f"[INFO] {log}")
    
    @classmethod
    def debug(cls, log: str) -> None:
        """
        Log a debug message if DEBUG level is enabled.
        
        Args:
            log: The message to log
        """
        if not cls._instance:
            cls._instance = Logger()
        
        if cls._allowed(LoggerPrintMode.DEBUG):
            print(f"[DEBUG] {log}")
    
    @classmethod
    def error(cls, log: str) -> None:
        """
        Log an error message if ERROR level is enabled.
        
        Args:
            log: The message to log
        """
        if not cls._instance:
            cls._instance = Logger()
        
        if cls._allowed(LoggerPrintMode.ERROR):
            print(f"[ERROR] {log}", file=sys.stderr)
    
    @classmethod
    def _allowed(cls, q_mode: LoggerPrintMode) -> bool:
        """
        Check if a logging level is enabled.
        
        Args:
            q_mode: The logging level to check
            
        Returns:
            True if the logging level is enabled, False otherwise
        """
        return q_mode in cls._print_modes