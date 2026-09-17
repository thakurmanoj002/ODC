import uuid
from datetime import datetime, timezone
from typing import List, Optional
from shared.models.requests import ActionRequest
from shared.models.responses import ActionResponse
from shared.constants.protocol import AllowedAction, ErrorCode
from controller.database.database import db
from controller.database.models import ComputerRecord
from controller.services.agent_client import agent_client
from controller.config.settings import controller_settings
from controller.utils.logging_config import logger


class ComputerService:
    def get_computers(self) -> List[ComputerRecord]:
        return db.get_all_computers()

    def get_computer(self, agent_id: str) -> Optional[ComputerRecord]:
        return db.get_computer_by_agent_id(agent_id)

    def remove_computer(self, agent_id: str):
        comp = db.get_computer_by_agent_id(agent_id)
        if comp:
            db.delete_computer(agent_id)
            db.log_activity(
                action="REMOVE_COMPUTER",
                status="SUCCESS",
                message=f"Removed computer {comp.display_name} from Controller",
                computer_id=agent_id,
                computer_name=comp.display_name,
            )

    def pair_and_add_computer(
        self, ip: str, port: int, pairing_code: str
    ) -> tuple[bool, str, Optional[ComputerRecord]]:
        health = agent_client.check_health(ip, port)
        if not health:
            return False, f"Unable to connect to Agent at {ip}:{port}. Verify Agent is running.", None

        pair_resp = agent_client.pair(
            ip=ip,
            port=port,
            controller_id=controller_settings.controller_id,
            controller_name=controller_settings.controller_name,
            pairing_code=pairing_code,
        )

        if not pair_resp.success or not pair_resp.auth_token:
            db.log_activity(
                action="PAIR_COMPUTER",
                status="FAILED",
                message=f"Pairing failed for {ip}:{port} - {pair_resp.message}",
            )
            return False, f"Pairing failed: {pair_resp.message}", None

        now = datetime.now(timezone.utc).isoformat()
        existing = db.get_computer_by_agent_id(pair_resp.agent_id)

        if existing:
            db.update_computer_details(
                agent_id=pair_resp.agent_id,
                display_name=health.computer_name,
                ip_address=ip,
                port=port,
                auth_token=pair_resp.auth_token,
            )
            db.update_computer_status(pair_resp.agent_id, "ONLINE", now)
            comp = db.get_computer_by_agent_id(pair_resp.agent_id)
        else:
            comp = ComputerRecord(
                id=None,
                agent_id=pair_resp.agent_id,
                display_name=health.computer_name,
                ip_address=ip,
                port=port,
                auth_token=pair_resp.auth_token,
                os_name="Windows",
                agent_version=health.agent_version,
                status="ONLINE",
                last_seen=now,
                created_at=now,
                updated_at=now,
            )
            comp = db.add_computer(comp)

        if health.capabilities:
            db.save_computer_capabilities(comp.agent_id, health.capabilities)

        db.log_activity(
            action="PAIR_COMPUTER",
            status="SUCCESS",
            message=f"Successfully paired and added computer {comp.display_name} ({comp.agent_id})",
            computer_id=comp.agent_id,
            computer_name=comp.display_name,
        )
        return True, "Pairing successful!", comp

    def update_all_statuses(self):
        computers = db.get_all_computers()
        now = datetime.now(timezone.utc).isoformat()
        for comp in computers:
            health = agent_client.check_health(comp.ip_address, comp.port)
            if health:
                db.update_computer_status(comp.agent_id, "ONLINE", now)
                if health.capabilities:
                    db.save_computer_capabilities(comp.agent_id, health.capabilities)
            else:
                if comp.status == "ONLINE":
                    db.log_activity(
                        action="HEALTH_CHECK",
                        status="WARNING",
                        message=f"Connection lost to {comp.display_name} ({comp.ip_address})",
                        computer_id=comp.agent_id,
                        computer_name=comp.display_name,
                    )
                db.update_computer_status(comp.agent_id, "OFFLINE", comp.last_seen)

    def get_computer_capabilities(self, agent_id: str) -> List[str]:
        return db.get_computer_capabilities(agent_id)

    # --- Dispatcher Helper ---
    def _execute_agent_action(self, agent_id: str, action: str, parameters: dict = None) -> ActionResponse:
        comp = db.get_computer_by_agent_id(agent_id)
        req_id = f"req-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        if not comp or comp.status == "OFFLINE":
            msg = f"Computer {comp.display_name if comp else agent_id} is OFFLINE."
            db.log_activity(
                action=action,
                status="FAILED",
                message=msg,
                computer_id=agent_id,
                computer_name=comp.display_name if comp else None,
                request_id=req_id,
            )
            return ActionResponse(
                success=False,
                request_id=req_id,
                action=action,
                message=msg,
                error_code=ErrorCode.OFFLINE.value,
                timestamp=now,
            )

        action_req = ActionRequest(
            request_id=req_id,
            action=action,
            timestamp=now,
            parameters=parameters or {},
        )

        resp = agent_client.send_action(comp.ip_address, comp.port, comp.auth_token, action_req)

        status_str = "SUCCESS" if resp.success else "FAILED"
        if action in (AllowedAction.RESTART_PC.value, AllowedAction.SHUTDOWN_PC.value) and resp.success:
            status_str = "COMMAND_SENT"

        db.log_activity(
            action=action,
            status=status_str,
            message=resp.message,
            computer_id=agent_id,
            computer_name=comp.display_name,
            request_id=req_id,
        )
        return resp

    # --- Phase 2 Service Actions ---
    def get_wifi_status(self, agent_id: str) -> ActionResponse:
        return self._execute_agent_action(agent_id, AllowedAction.WIFI_STATUS.value)

    def wifi_on(self, agent_id: str) -> ActionResponse:
        return self._execute_agent_action(agent_id, AllowedAction.WIFI_ON.value)

    def wifi_off(self, agent_id: str) -> ActionResponse:
        return self._execute_agent_action(agent_id, AllowedAction.WIFI_OFF.value)

    def lock_pc(self, agent_id: str) -> ActionResponse:
        return self._execute_agent_action(agent_id, AllowedAction.LOCK_PC.value)

    def restart_pc(self, agent_id: str) -> ActionResponse:
        return self._execute_agent_action(agent_id, AllowedAction.RESTART_PC.value)

    def shutdown_pc(self, agent_id: str) -> ActionResponse:
        return self._execute_agent_action(agent_id, AllowedAction.SHUTDOWN_PC.value)

    # --- Phase 3 Service Actions ---
    def get_running_applications(self, agent_id: str) -> ActionResponse:
        return self._execute_agent_action(agent_id, AllowedAction.GET_RUNNING_APPLICATIONS.value)

    def start_allowed_application(self, agent_id: str, app_id: str) -> ActionResponse:
        return self._execute_agent_action(agent_id, AllowedAction.START_ALLOWED_APP.value, parameters={"app_id": app_id})

    def stop_allowed_application(self, agent_id: str, app_id: str) -> ActionResponse:
        return self._execute_agent_action(agent_id, AllowedAction.STOP_ALLOWED_APP.value, parameters={"app_id": app_id})

    # --- Phase 4 Service Actions ---
    def get_directory(self, agent_id: str, root_id: str, relative_path: str = "") -> ActionResponse:
        return self._execute_agent_action(
            agent_id,
            AllowedAction.GET_DIRECTORY.value,
            parameters={"root_id": root_id, "relative_path": relative_path},
        )

    def get_file_metadata(self, agent_id: str, root_id: str, relative_path: str) -> ActionResponse:
        return self._execute_agent_action(
            agent_id,
            AllowedAction.GET_FILE_METADATA.value,
            parameters={"root_id": root_id, "relative_path": relative_path},
        )

    def create_folder(self, agent_id: str, root_id: str, relative_parent_path: str, folder_name: str) -> ActionResponse:
        return self._execute_agent_action(
            agent_id,
            AllowedAction.CREATE_FOLDER.value,
            parameters={"root_id": root_id, "relative_parent_path": relative_parent_path, "folder_name": folder_name},
        )

    def rename_path(self, agent_id: str, root_id: str, relative_path: str, new_name: str) -> ActionResponse:
        return self._execute_agent_action(
            agent_id,
            AllowedAction.RENAME_PATH.value,
            parameters={"root_id": root_id, "relative_path": relative_path, "new_name": new_name},
        )

    def delete_path(self, agent_id: str, root_id: str, relative_path: str) -> ActionResponse:
        return self._execute_agent_action(
            agent_id,
            AllowedAction.DELETE_PATH.value,
            parameters={"root_id": root_id, "relative_path": relative_path},
        )


computer_service = ComputerService()
