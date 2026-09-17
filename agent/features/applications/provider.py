import os
import subprocess
import psutil
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from shared.models.requests import ActionRequest
from shared.models.responses import ActionResponse
from shared.constants.protocol import AllowedAction, ErrorCode
from agent.features.base import BaseFeature
from agent.features.applications.base import BaseApplicationManager
from agent.features.applications.allowlist import app_allowlist
import agent.config.settings as settings_module
from agent.utils.logging_config import logger

PROTECTED_PROCESSES = {
    "system",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "explorer.exe",
    "system idle process",
}


class WindowsApplicationManager(BaseApplicationManager):
    def get_running_applications(self) -> List[Dict[str, Any]]:
        running = []
        allowlist_apps = app_allowlist.get_all_apps()

        try:
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
                try:
                    pname = proc.info["name"] or ""
                    if not pname or pname.lower() in PROTECTED_PROCESSES:
                        continue

                    # Check if process matches any allowlist application
                    for app_id, app_info in allowlist_apps.items():
                        if app_info["executable_name"].lower() == pname.lower():
                            mem_mb = round((proc.info["memory_info"].rss if proc.info["memory_info"] else 0) / (1024 * 1024), 1)
                            running.append({
                                "app_id": app_id,
                                "name": app_info["display_name"],
                                "executable": pname,
                                "pid": proc.info["pid"],
                                "cpu_percent": proc.info["cpu_percent"] or 0.0,
                                "memory_mb": mem_mb,
                                "status": "Running",
                            })
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            logger.error(f"Error listing running applications: {e}")

        return running

    def start_allowed_application(self, app_id: str) -> Tuple[bool, str, Optional[str]]:
        if settings_module.agent_settings.safe_mode:
            logger.warning(f"START_ALLOWED_APP '{app_id}' blocked by SAFE_MODE guard.")
            return False, "Real machine execution is disabled in safe mode.", ErrorCode.SAFE_MODE_BLOCKED.value

        app_info = app_allowlist.get_app(app_id)
        if not app_info:
            return False, f"Application '{app_id}' is not in the allowed applications list.", ErrorCode.APP_NOT_ALLOWED.value

        if not app_info.get("enabled", True):
            return False, f"Application '{app_info['display_name']}' is disabled.", ErrorCode.APP_DISABLED.value

        exec_path = app_info.get("executable_path")
        exec_name = app_info.get("executable_name")

        if not exec_path or not os.path.exists(exec_path):
            # Try launching by executable name if path doesn't exist
            exec_target = exec_name
        else:
            exec_target = exec_path

        try:
            subprocess.Popen([exec_target])
            logger.info(f"Launched allowed application: {app_info['display_name']} ({exec_target})")
            return True, f"Application '{app_info['display_name']}' started successfully.", None
        except Exception as e:
            logger.error(f"Failed to start allowed application '{app_id}': {e}")
            return False, f"Failed to launch application: {str(e)}", ErrorCode.EXECUTION_FAILED.value

    def stop_allowed_application(self, app_id: str) -> Tuple[bool, str, Optional[str]]:
        if settings_module.agent_settings.safe_mode:
            logger.warning(f"STOP_ALLOWED_APP '{app_id}' blocked by SAFE_MODE guard.")
            return False, "Real machine execution is disabled in safe mode.", ErrorCode.SAFE_MODE_BLOCKED.value

        app_info = app_allowlist.get_app(app_id)
        if not app_info:
            return False, f"Application '{app_id}' is not in the allowed applications list.", ErrorCode.APP_NOT_ALLOWED.value

        if not app_info.get("manageable", True):
            return False, f"Application '{app_info['display_name']}' is not marked manageable.", ErrorCode.PERMISSION_DENIED.value

        exec_name = app_info.get("executable_name", "").lower()
        if exec_name in PROTECTED_PROCESSES:
            return False, f"Process '{exec_name}' is a protected Windows system process.", ErrorCode.PROTECTED_PROCESS.value

        terminated_count = 0
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    pname = (proc.info["name"] or "").lower()
                    if pname == exec_name and pname not in PROTECTED_PROCESSES:
                        proc.terminate()
                        terminated_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if terminated_count > 0:
                logger.info(f"Stopped {terminated_count} process instance(s) of '{app_info['display_name']}'")
                return True, f"Application '{app_info['display_name']}' stopped successfully.", None
            else:
                return False, f"No running instance of '{app_info['display_name']}' was found.", ErrorCode.NOT_FOUND.value
        except Exception as e:
            logger.error(f"Error stopping application '{app_id}': {e}")
            return False, f"Failed to stop application: {str(e)}", ErrorCode.EXECUTION_FAILED.value


class MockApplicationManager(BaseApplicationManager):
    def __init__(self):
        self.running_apps = [
            {
                "app_id": "excel",
                "name": "Microsoft Excel",
                "executable": "EXCEL.EXE",
                "pid": 4321,
                "cpu_percent": 2.5,
                "memory_mb": 145.2,
                "status": "Running",
            }
        ]

    def get_running_applications(self) -> List[Dict[str, Any]]:
        return self.running_apps

    def start_allowed_application(self, app_id: str) -> Tuple[bool, str, Optional[str]]:
        app_info = app_allowlist.get_app(app_id)
        if not app_info:
            return False, f"Application '{app_id}' is not allowed.", ErrorCode.APP_NOT_ALLOWED.value
        if not app_info.get("enabled", True):
            return False, f"Application '{app_info['display_name']}' is disabled.", ErrorCode.APP_DISABLED.value

        # Add to mock running list if not already present
        if not any(a["app_id"] == app_id for a in self.running_apps):
            self.running_apps.append({
                "app_id": app_id,
                "name": app_info["display_name"],
                "executable": app_info["executable_name"],
                "pid": 8888,
                "cpu_percent": 1.0,
                "memory_mb": 50.0,
                "status": "Running",
            })
        return True, f"Application '{app_info['display_name']}' started (Mocked).", None

    def stop_allowed_application(self, app_id: str) -> Tuple[bool, str, Optional[str]]:
        app_info = app_allowlist.get_app(app_id)
        if not app_info:
            return False, f"Application '{app_id}' is not allowed.", ErrorCode.APP_NOT_ALLOWED.value

        matching = [a for a in self.running_apps if a["app_id"] == app_id]
        if matching:
            self.running_apps = [a for a in self.running_apps if a["app_id"] != app_id]
            return True, f"Application '{app_info['display_name']}' stopped (Mocked).", None
        else:
            return False, f"No running instance of '{app_info['display_name']}' found (Mocked).", ErrorCode.NOT_FOUND.value


class ApplicationFeature(BaseFeature):
    def __init__(self, manager: BaseApplicationManager = None):
        self.manager = manager or WindowsApplicationManager()

    @property
    def name(self) -> str:
        return "applications"

    def register_actions(self, registry) -> None:
        registry.register(
            action_id=AllowedAction.GET_RUNNING_APPLICATIONS.value,
            feature=self.name,
            description="Retrieve running user applications and metrics",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_get_running_apps,
        )
        registry.register(
            action_id=AllowedAction.START_ALLOWED_APP.value,
            feature=self.name,
            description="Start an application configured in local allowlist",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_start_app,
        )
        registry.register(
            action_id=AllowedAction.STOP_ALLOWED_APP.value,
            feature=self.name,
            description="Stop instances of a configured manageable application",
            permission_level="ADMIN",
            confirmation_required=True,
            handler=self.handle_stop_app,
        )

    def handle_get_running_apps(self, req: ActionRequest) -> ActionResponse:
        apps = self.manager.get_running_applications()
        all_allowed = app_allowlist.get_all_apps()
        return ActionResponse(
            success=True,
            request_id=req.request_id,
            action=req.action,
            message="Running applications retrieved successfully",
            data={
                "running_apps": apps,
                "allowed_apps": list(all_allowed.values()),
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_start_app(self, req: ActionRequest) -> ActionResponse:
        app_id = req.parameters.get("app_id", "").strip()
        if not app_id:
            return ActionResponse(
                success=False,
                request_id=req.request_id,
                action=req.action,
                message="Parameter 'app_id' is required.",
                error_code=ErrorCode.INVALID_REQUEST.value,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        success, msg, err_code = self.manager.start_allowed_application(app_id)
        return ActionResponse(
            success=success,
            request_id=req.request_id,
            action=req.action,
            message=msg,
            error_code=err_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_stop_app(self, req: ActionRequest) -> ActionResponse:
        app_id = req.parameters.get("app_id", "").strip()
        if not app_id:
            return ActionResponse(
                success=False,
                request_id=req.request_id,
                action=req.action,
                message="Parameter 'app_id' is required.",
                error_code=ErrorCode.INVALID_REQUEST.value,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        success, msg, err_code = self.manager.stop_allowed_application(app_id)
        return ActionResponse(
            success=success,
            request_id=req.request_id,
            action=req.action,
            message=msg,
            error_code=err_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
