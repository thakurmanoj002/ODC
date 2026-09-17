from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional


class BaseFileManager(ABC):
    @abstractmethod
    def get_directory(self, root_id: str, relative_path: str) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """List contents of an approved logical root directory."""
        pass

    @abstractmethod
    def get_file_metadata(self, root_id: str, relative_path: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Retrieve metadata for a file or directory."""
        pass

    @abstractmethod
    def create_folder(self, root_id: str, relative_parent_path: str, folder_name: str) -> Tuple[bool, str, Optional[str]]:
        """Create a directory within an approved logical root."""
        pass

    @abstractmethod
    def rename_path(self, root_id: str, relative_path: str, new_name: str) -> Tuple[bool, str, Optional[str]]:
        """Rename a file or directory within an approved logical root."""
        pass

    @abstractmethod
    def delete_path(self, root_id: str, relative_path: str) -> Tuple[bool, str, Optional[str]]:
        """Delete a file or directory within an approved logical root."""
        pass
