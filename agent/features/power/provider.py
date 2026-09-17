import ctypes
import subprocess
from datetime import datetime, timezone
from typing import Tuple, Optional
from shared.models.requests import ActionRequest
from shared.models.responses import ActionResponse
from shared.constants.protocol import AllowedAction, ErrorCode
from agent.features.base import BaseFeature
from agent.features.power.base import BasePowerManager
import agent.config.settings as settings_module
from agent.utils.logging_config import logger


class WindowsPowerManager(BasePowerManager):
    def lock(self) -> Tuple[bool, str, Optional[str]]:
        if settings_module.agent_settings.safe_mode:
            logger.warning("LOCK_PC blocked by SAFE_MODE guard.")
            return False, "Real machine execution is disabled in safe mode.", ErrorCode.SAFE_MODE_BLOCKED.value

        try:
            res = ctypes.windll.user32.LockWorkStation()
            if res != 0:
                logger.info("Workstation locked successfully via LockWorkStation API")
                return True, "Workstation session locked successfully.", None
            else:
                logger.error("LockWorkStation returned error code 0")
                return False, "Failed to lock workstation session.", ErrorCode.POWER_OPERATION_FAILED.value
        except Exception as e:
            logger.error(f"Lock Workstation error: {e}")
            return False, f"Lock workstation failed: {str(e)}", ErrorCode.POWER_OPERATION_FAILED.value

    def restart(self) -> Tuple[bool, str, Optional[str]]:
        if settings_module.agent_settings.safe_mode:
            logger.warning("RESTART_PC blocked by SAFE_MODE guard.")
            return False, "Real machine execution is disabled in safe mode.", ErrorCode.SAFE_MODE_BLOCKED.value

        try:
            cmd = ["shutdown", "/r", "/t", "5", "/c", "Restart requested from LAN Office Control Center"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                logger.info("Restart command issued successfully (5-second delay)")
                return True, "Restart command sent successfully. System is rebooting.", None
            else:
                err_msg = res.stderr or res.stdout
                logger.error(f"Restart command failed: {err_msg}")
                return False, f"Restart command failed: {err_msg}", ErrorCode.POWER_OPERATION_FAILED.value
        except Exception as e:
            logger.error(f"Restart operation exception: {e}")
            return False, f"Restart operation failed: {str(e)}", ErrorCode.POWER_OPERATION_FAILED.value

    def shutdown(self) -> Tuple[bool, str, Optional[str]]:
        if settings_module.agent_settings.safe_mode:
            logger.warning("SHUTDOWN_PC blocked by SAFE_MODE guard.")
            return False, "Real machine execution is disabled in safe mode.", ErrorCode.SAFE_MODE_BLOCKED.value

        try:
            cmd = ["shutdown", "/s", "/t", "5", "/c", "Shutdown requested from LAN Office Control Center"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                logger.info("Shutdown command issued successfully (5-second delay)")
                return True, "Shutdown command sent successfully. System is powering off.", None
            else:
                err_msg = res.stderr or res.stdout
                logger.error(f"Shutdown command failed: {err_msg}")
                return False, f"Shutdown command failed: {err_msg}", ErrorCode.POWER_OPERATION_FAILED.value
        except Exception as e:
            logger.error(f"Shutdown operation exception: {e}")
            return False, f"Shutdown operation failed: {str(e)}", ErrorCode.POWER_OPERATION_FAILED.value


class PowerFeature(BaseFeature):
    def __init__(self, manager: BasePowerManager = None):
        self.manager = manager or WindowsPowerManager()

    @property
    def name(self) -> str:
        return "power"

    def register_actions(self, registry) -> None:
        registry.register(
            action_id=AllowedAction.LOCK_PC.value,
            feature=self.name,
            description="Lock active Windows user session",
            permission_level="NORMAL",
            confirmation_required=True,
            handler=self.handle_lock_pc,
        )
        registry.register(
            action_id=AllowedAction.RESTART_PC.value,
            feature=self.name,
            description="Initiate restart of Windows operating system",
            permission_level="ADMIN",
            confirmation_required=True,
            handler=self.handle_restart_pc,
        )
        registry.register(
            action_id=AllowedAction.SHUTDOWN_PC.value,
            feature=self.name,
            description="Initiate shutdown of Windows operating system",
            permission_level="ADMIN",
            confirmation_required=True,
            handler=self.handle_shutdown_pc,
        )

    def handle_lock_pc(self, req: ActionRequest) -> ActionResponse:
        success, msg, err_code = self.manager.lock()
        return ActionResponse(
            success=success,
            request_id=req.request_id,
            action=req.action,
            message=msg,
            error_code=err_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_restart_pc(self, req: ActionRequest) -> ActionResponse:
        success, msg, err_code = self.manager.restart()
        return ActionResponse(
            success=success,
            request_id=req.request_id,
            action=req.action,
            message=msg,
            error_code=err_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_shutdown_pc(self, req: ActionRequest) -> ActionResponse:
        success, msg, err_code = self.manager.shutdown()
        return ActionResponse(
            success=success,
            request_id=req.request_id,
            action=req.action,
            message=msg,
            error_code=err_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
