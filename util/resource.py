# lapras/util/resource.py
import os
import io
from typing import Optional, Union, IO

class Resource:
    """
    Utility class for accessing resources.
    """
    
    # Default to the current directory, but can be overridden
    RESOURCE_PATH = os.environ.get('LAPRAS_RESOURCE_DIR', os.getcwd())
    
    @staticmethod
    def path_of(resource_name: str) -> str:
        """
        Get the full path of a resource.
        
        Args:
            resource_name: The name of the resource
            
        Returns:
            The full path to the resource
        """
        return os.path.join(Resource.RESOURCE_PATH, resource_name)
    
    @staticmethod
    def get_stream(resource_name: str) -> Optional[IO[bytes]]:
        """
        Get an input stream for a resource.
        
        Args:
            resource_name: The name of the resource
            
        Returns:
            A file object for the resource, or None if the resource doesn't exist
        """
        path = Resource.path_of(resource_name)
        try:
            return open(path, 'rb')
        except FileNotFoundError:
            return None
    
    @staticmethod
    def get_content(resource_name: str) -> Optional[bytes]:
        """
        Get the content of a resource as bytes.
        
        Args:
            resource_name: The name of the resource
            
        Returns:
            The content of the resource as bytes, or None if the resource doesn't exist
        """
        stream = Resource.get_stream(resource_name)
        if stream:
            try:
                return stream.read()
            finally:
                stream.close()
        return None
    
    @staticmethod
    def get_text(resource_name: str, encoding: str = 'utf-8') -> Optional[str]:
        """
        Get the content of a resource as text.
        
        Args:
            resource_name: The name of the resource
            encoding: The encoding to use when reading the resource
            
        Returns:
            The content of the resource as text, or None if the resource doesn't exist
        """
        content = Resource.get_content(resource_name)
        if content:
            return content.decode(encoding)
        return None