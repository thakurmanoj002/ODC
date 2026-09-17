from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional


class BaseApplicationManager(ABC):
    @abstractmethod
    def get_running_applications(self) -> List[Dict[str, Any]]:
        """Fetch running allowed applications."""
        pass

    @abstractmethod
    def start_allowed_application(self, app_id: str) -> Tuple[bool, str, Optional[str]]:
        """Start an application configured in local allowlist."""
        pass

    @abstractmethod
    def stop_allowed_application(self, app_id: str) -> Tuple[bool, str, Optional[str]]:
        """Stop instances of a configured manageable application."""
        pass
