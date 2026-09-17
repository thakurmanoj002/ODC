from abc import ABC, abstractmethod
from typing import List, Dict, Any
from shared.models.responses import SystemInfoResponse, NetworkInfoResponse


class BaseFeature(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique feature name, e.g., 'system', 'network'."""
        pass

    @abstractmethod
    def register_actions(self, registry) -> None:
        """Register feature-specific action handlers with the ActionRegistry."""
        pass


class BaseSystemInfoProvider(ABC):
    @abstractmethod
    def get_system_info(self) -> SystemInfoResponse:
        """Fetch system information metrics."""
        pass


class BaseNetworkManager(ABC):
    @abstractmethod
    def get_network_info(self) -> NetworkInfoResponse:
        """Fetch network information details."""
        pass
    
    @abstractmethod
    def get_local_ip(self) -> str:
        """Get primary LAN IP address."""
        pass
