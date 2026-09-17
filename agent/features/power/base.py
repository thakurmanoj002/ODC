from abc import ABC, abstractmethod
from typing import Tuple, Optional


class BasePowerManager(ABC):
    @abstractmethod
    def lock(self) -> Tuple[bool, str, Optional[str]]:
        """Lock workstation session."""
        pass

    @abstractmethod
    def restart(self) -> Tuple[bool, str, Optional[str]]:
        """Initiate system restart."""
        pass

    @abstractmethod
    def shutdown(self) -> Tuple[bool, str, Optional[str]]:
        """Initiate system shutdown."""
        pass
