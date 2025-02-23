class LaprasException(Exception):
    """Base exception class for Lapras middleware."""
    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message)
        self.cause = cause