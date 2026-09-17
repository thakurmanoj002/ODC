import platform
import time
import psutil
from datetime import datetime, timezone
from shared.models.requests import ActionRequest
from shared.models.responses import SystemInfoResponse, ActionResponse
from shared.constants.protocol import AllowedAction
from agent.features.base import BaseFeature, BaseSystemInfoProvider
import agent.config.settings as settings_module


class WindowsSystemInfoProvider(BaseSystemInfoProvider):
    def get_system_info(self) -> SystemInfoResponse:
        s = settings_module.agent_settings
        vm = psutil.virtual_memory()
        total_ram_gb = round(vm.total / (1024 ** 3), 2)
        used_ram_gb = round(vm.used / (1024 ** 3), 2)

        try:
            disk = psutil.disk_usage("/")
            disk_pct = disk.percent
        except Exception:
            disk_pct = 0.0

        try:
            boot_time = psutil.boot_time()
            uptime_sec = round(time.time() - boot_time, 2)
        except Exception:
            uptime_sec = 0.0

        return SystemInfoResponse(
            computer_name=s.computer_name,
            os_name=platform.system(),
            os_version=f"{platform.release()} ({platform.version()})",
            cpu_usage=psutil.cpu_percent(interval=None),
            ram_usage=vm.percent,
            total_ram_gb=total_ram_gb,
            used_ram_gb=used_ram_gb,
            disk_usage=disk_pct,
            uptime_seconds=uptime_sec,
            agent_version=s.agent_version,
        )


class SystemFeature(BaseFeature):
    def __init__(self, provider: BaseSystemInfoProvider = None):
        self.provider = provider or WindowsSystemInfoProvider()

    @property
    def name(self) -> str:
        return "system"

    def register_actions(self, registry) -> None:
        registry.register(
            action_id=AllowedAction.GET_SYSTEM_INFO.value,
            feature=self.name,
            description="Retrieve real-time hardware metrics (CPU, RAM, Disk, Uptime)",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_get_system_info,
        )
        registry.register(
            action_id=AllowedAction.GET_STATUS.value,
            feature=self.name,
            description="Retrieve basic system status overview",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_get_system_info,
        )

    def handle_get_system_info(self, req: ActionRequest) -> ActionResponse:
        sys_info = self.provider.get_system_info()
        return ActionResponse(
            success=True,
            request_id=req.request_id,
            action=req.action,
            message="System info retrieved successfully",
            data=sys_info.model_dump(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
