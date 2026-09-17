import socket
from datetime import datetime, timezone
from typing import Optional
from shared.models.requests import ActionRequest
from shared.models.responses import NetworkInfoResponse, ActionResponse
from shared.constants.protocol import AllowedAction, ErrorCode
from agent.features.base import BaseFeature, BaseNetworkManager
from agent.features.network.wifi import WindowsWifiManager


class WindowsNetworkManager(BaseNetworkManager):
    def __init__(self, wifi_manager: Optional[WindowsWifiManager] = None):
        self.wifi_manager = wifi_manager or WindowsWifiManager()

    def get_local_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            try:
                ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def get_network_info(self) -> NetworkInfoResponse:
        return NetworkInfoResponse(
            local_ip=self.get_local_ip(),
            hostname=socket.gethostname(),
            connection_info="LAN Active",
            network_state="CONNECTED",
        )


class NetworkFeature(BaseFeature):
    def __init__(self, manager: BaseNetworkManager = None, wifi_manager: WindowsWifiManager = None):
        self.manager = manager or WindowsNetworkManager(wifi_manager=wifi_manager)
        self.wifi_manager = wifi_manager or getattr(self.manager, "wifi_manager", WindowsWifiManager())

    @property
    def name(self) -> str:
        return "network"

    def register_actions(self, registry) -> None:
        registry.register(
            action_id=AllowedAction.GET_NETWORK_INFO.value,
            feature=self.name,
            description="Retrieve network state, LAN IP, and hostname details",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_get_network_info,
        )

        # Register Wi-Fi actions if Wi-Fi capability is available or supported
        wifi_info = self.wifi_manager.get_wifi_status()
        if wifi_info.get("available", False):
            registry.register(
                action_id=AllowedAction.WIFI_STATUS.value,
                feature=self.name,
                description="Retrieve Wi-Fi adapter connection state and SSID",
                permission_level="NORMAL",
                confirmation_required=False,
                handler=self.handle_wifi_status,
            )
            registry.register(
                action_id=AllowedAction.WIFI_ON.value,
                feature=self.name,
                description="Enable local Wi-Fi adapter",
                permission_level="ADMIN",
                confirmation_required=False,
                handler=self.handle_wifi_on,
            )
            registry.register(
                action_id=AllowedAction.WIFI_OFF.value,
                feature=self.name,
                description="Disable local Wi-Fi adapter",
                permission_level="ADMIN",
                confirmation_required=True,
                handler=self.handle_wifi_off,
            )

    def handle_get_network_info(self, req: ActionRequest) -> ActionResponse:
        net_info = self.manager.get_network_info()
        return ActionResponse(
            success=True,
            request_id=req.request_id,
            action=req.action,
            message="Network info retrieved successfully",
            data=net_info.model_dump(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_wifi_status(self, req: ActionRequest) -> ActionResponse:
        status_data = self.wifi_manager.get_wifi_status()
        if not status_data["available"]:
            return ActionResponse(
                success=False,
                request_id=req.request_id,
                action=req.action,
                message="Wi-Fi adapter is not available on this computer.",
                error_code=ErrorCode.WIFI_ADAPTER_NOT_FOUND.value,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        return ActionResponse(
            success=True,
            request_id=req.request_id,
            action=req.action,
            message="Wi-Fi status retrieved successfully",
            data=status_data,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_wifi_on(self, req: ActionRequest) -> ActionResponse:
        success, msg, err_code = self.wifi_manager.set_wifi_state(enable=True)
        return ActionResponse(
            success=success,
            request_id=req.request_id,
            action=req.action,
            message=msg,
            error_code=err_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_wifi_off(self, req: ActionRequest) -> ActionResponse:
        success, msg, err_code = self.wifi_manager.set_wifi_state(enable=False)
        return ActionResponse(
            success=success,
            request_id=req.request_id,
            action=req.action,
            message=msg,
            error_code=err_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
