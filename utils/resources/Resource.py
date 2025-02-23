from pathlib import Path
import io
import pkg_resources
import logging

logger = logging.getLogger(__name__)

class Resource:
    @staticmethod
    def get_stream(resource_path: str) -> io.IOBase:
        """Get a file stream for a resource."""
        try:
            # First try package resources
            return pkg_resources.resource_stream(__name__, resource_path)
        except Exception:
            # Fall back to local file system
            path = Path(resource_path)
            if path.exists():
                return open(path, 'rb')
            raise FileNotFoundError(f"Resource not found: {resource_path}")

    @staticmethod
    def path_of(resource_path: str) -> str:
        """Get the absolute path of a resource."""
        try:
            return pkg_resources.resource_filename(__name__, resource_path)
        except Exception:
            path = Path(resource_path)
            if path.exists():
                return str(path.absolute())
            raise FileNotFoundError(f"Resource not found: {resource_path}")