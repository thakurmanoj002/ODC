import os
import shutil
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from shared.models.requests import ActionRequest
from shared.models.responses import ActionResponse
from shared.constants.protocol import AllowedAction, ErrorCode
from agent.features.base import BaseFeature
from agent.features.files.base import BaseFileManager
from agent.features.files.sandbox import path_sandbox
from agent.features.files.transfer import transfer_manager
import agent.config.settings as settings_module
from agent.utils.logging_config import logger


class WindowsFileManager(BaseFileManager):
    def get_directory(self, root_id: str, relative_path: str) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        ok, resolved_path, root_base, err = path_sandbox.resolve_and_validate(root_id, relative_path)
        if not ok:
            return False, [], err

        if not os.path.exists(resolved_path):
            return False, [], ErrorCode.NOT_FOUND.value

        if not os.path.isdir(resolved_path):
            return False, [], ErrorCode.INVALID_REQUEST.value

        items = []
        try:
            for entry in os.scandir(resolved_path):
                try:
                    stat = entry.stat()
                    is_dir = entry.is_dir()
                    ext = os.path.splitext(entry.name)[1] if not is_dir else ""
                    mod_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                    items.append({
                        "name": entry.name,
                        "type": "folder" if is_dir else "file",
                        "size": 0 if is_dir else stat.st_size,
                        "modified": mod_time,
                        "extension": ext,
                    })
                except Exception:
                    continue
            return True, items, None
        except Exception as e:
            logger.error(f"Error listing directory '{resolved_path}': {e}")
            return False, [], ErrorCode.EXECUTION_FAILED.value

    def get_file_metadata(self, root_id: str, relative_path: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        ok, resolved_path, root_base, err = path_sandbox.resolve_and_validate(root_id, relative_path)
        if not ok:
            return False, None, err

        if not os.path.exists(resolved_path):
            return False, None, ErrorCode.NOT_FOUND.value

        try:
            stat = os.stat(resolved_path)
            is_dir = os.path.isdir(resolved_path)
            ext = os.path.splitext(resolved_path)[1] if not is_dir else ""
            meta = {
                "name": os.path.basename(resolved_path),
                "type": "folder" if is_dir else "file",
                "size": 0 if is_dir else stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "extension": ext,
                "root_id": root_id,
            }
            return True, meta, None
        except Exception as e:
            logger.error(f"Error fetching metadata for '{resolved_path}': {e}")
            return False, None, ErrorCode.EXECUTION_FAILED.value

    def create_folder(self, root_id: str, relative_parent_path: str, folder_name: str) -> Tuple[bool, str, Optional[str]]:
        if settings_module.agent_settings.safe_mode:
            logger.warning("CREATE_FOLDER blocked by SAFE_MODE guard.")
            return False, "Real machine execution is disabled in safe mode.", ErrorCode.SAFE_MODE_BLOCKED.value

        clean_name = (folder_name or "").strip()
        if not clean_name or any(c in clean_name for c in '<>:"/\\|?*'):
            return False, "Invalid folder name characters.", ErrorCode.INVALID_REQUEST.value

        rel_path = os.path.join(relative_parent_path or "", clean_name)
        ok, resolved_path, root_base, err = path_sandbox.resolve_and_validate(root_id, rel_path)
        if not ok:
            return False, "Invalid folder target path.", err

        if os.path.exists(resolved_path):
            return False, f"Folder '{clean_name}' already exists.", ErrorCode.FILE_EXISTS.value

        try:
            os.makedirs(resolved_path, exist_ok=True)
            logger.info(f"Created folder: '{resolved_path}'")
            return True, f"Folder '{clean_name}' created successfully.", None
        except Exception as e:
            logger.error(f"Failed to create folder '{resolved_path}': {e}")
            return False, f"Failed to create folder: {str(e)}", ErrorCode.EXECUTION_FAILED.value

    def rename_path(self, root_id: str, relative_path: str, new_name: str) -> Tuple[bool, str, Optional[str]]:
        if settings_module.agent_settings.safe_mode:
            logger.warning("RENAME_PATH blocked by SAFE_MODE guard.")
            return False, "Real machine execution is disabled in safe mode.", ErrorCode.SAFE_MODE_BLOCKED.value

        clean_new = (new_name or "").strip()
        if not clean_new or any(c in clean_new for c in '<>:"/\\|?*'):
            return False, "Invalid new filename characters.", ErrorCode.INVALID_REQUEST.value

        ok, target_resolved, root_base, err = path_sandbox.resolve_and_validate(root_id, relative_path)
        if not ok:
            return False, "Target path validation failed.", err

        if not os.path.exists(target_resolved):
            return False, "Target file or folder not found.", ErrorCode.NOT_FOUND.value

        parent_dir = os.path.dirname(target_resolved)
        new_resolved = os.path.abspath(os.path.join(parent_dir, clean_new))

        # Commonpath check for new name to prevent traversal
        if os.path.commonpath([new_resolved, root_base]) != root_base:
            return False, "Renamed path escapes root boundary.", ErrorCode.PATH_TRAVERSAL_DETECTED.value

        if os.path.exists(new_resolved):
            return False, f"A file or folder named '{clean_new}' already exists.", ErrorCode.FILE_EXISTS.value

        try:
            os.rename(target_resolved, new_resolved)
            logger.info(f"Renamed '{target_resolved}' -> '{new_resolved}'")
            return True, f"Renamed to '{clean_new}' successfully.", None
        except Exception as e:
            logger.error(f"Failed to rename '{target_resolved}': {e}")
            return False, f"Failed to rename: {str(e)}", ErrorCode.EXECUTION_FAILED.value

    def delete_path(self, root_id: str, relative_path: str) -> Tuple[bool, str, Optional[str]]:
        if settings_module.agent_settings.safe_mode:
            logger.warning("DELETE_PATH blocked by SAFE_MODE guard.")
            return False, "Real machine execution is disabled in safe mode.", ErrorCode.SAFE_MODE_BLOCKED.value

        ok, target_resolved, root_base, err = path_sandbox.resolve_and_validate(root_id, relative_path)
        if not ok:
            return False, "Target path validation failed.", err

        if not os.path.exists(target_resolved):
            return False, "Target file or folder not found.", ErrorCode.NOT_FOUND.value

        # Prevent root path deletion
        if target_resolved == root_base:
            return False, "Deletion of approved root directory is strictly prohibited.", ErrorCode.PERMISSION_DENIED.value

        try:
            if os.path.isdir(target_resolved):
                shutil.rmtree(target_resolved)
                logger.info(f"Deleted folder tree: '{target_resolved}'")
                return True, "Folder and its contents deleted successfully.", None
            else:
                os.remove(target_resolved)
                logger.info(f"Deleted file: '{target_resolved}'")
                return True, "File deleted successfully.", None
        except Exception as e:
            logger.error(f"Failed to delete '{target_resolved}': {e}")
            return False, f"Failed to delete: {str(e)}", ErrorCode.EXECUTION_FAILED.value


class MockFileSystemManager(BaseFileManager):
    def __init__(self):
        self.mock_items = {
            "shared": [
                {"name": "Company_Policy.docx", "type": "file", "size": 45056, "modified": "2026-09-17T12:00:00Z", "extension": ".docx"},
                {"name": "Q3_Report.xlsx", "type": "file", "size": 128000, "modified": "2026-09-17T12:00:00Z", "extension": ".xlsx"},
                {"name": "ProjectTemplates", "type": "folder", "size": 0, "modified": "2026-09-17T12:00:00Z", "extension": ""},
            ],
            "documents": [
                {"name": "MeetingNotes.txt", "type": "file", "size": 1024, "modified": "2026-09-17T12:00:00Z", "extension": ".txt"},
            ],
        }

    def get_directory(self, root_id: str, relative_path: str) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        ok, resolved_path, root_base, err = path_sandbox.resolve_and_validate(root_id, relative_path)
        if not ok:
            return False, [], err
        items = self.mock_items.get(root_id.lower(), [])
        return True, items, None

    def get_file_metadata(self, root_id: str, relative_path: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        ok, resolved_path, root_base, err = path_sandbox.resolve_and_validate(root_id, relative_path)
        if not ok:
            return False, None, err
        items = self.mock_items.get(root_id.lower(), [])
        fname = os.path.basename(relative_path)
        for item in items:
            if item["name"].lower() == fname.lower():
                return True, {
                    "name": item["name"],
                    "type": item["type"],
                    "size": item["size"],
                    "created": "2026-09-17T12:00:00Z",
                    "modified": item["modified"],
                    "extension": item["extension"],
                    "root_id": root_id,
                }, None
        return False, None, ErrorCode.NOT_FOUND.value

    def create_folder(self, root_id: str, relative_parent_path: str, folder_name: str) -> Tuple[bool, str, Optional[str]]:
        rel_path = os.path.join(relative_parent_path or "", folder_name or "")
        ok, resolved_path, root_base, err = path_sandbox.resolve_and_validate(root_id, rel_path)
        if not ok:
            return False, "Validation failed.", err
        items = self.mock_items.setdefault(root_id.lower(), [])
        for item in items:
            if item["name"].lower() == (folder_name or "").lower():
                return False, f"Folder '{folder_name}' already exists.", ErrorCode.FILE_EXISTS.value
        items.append({
            "name": folder_name,
            "type": "folder",
            "size": 0,
            "modified": "2026-09-17T12:00:00Z",
            "extension": "",
        })
        return True, f"Folder '{folder_name}' created (Mocked).", None

    def rename_path(self, root_id: str, relative_path: str, new_name: str) -> Tuple[bool, str, Optional[str]]:
        ok, resolved_path, root_base, err = path_sandbox.resolve_and_validate(root_id, relative_path)
        if not ok:
            return False, "Validation failed.", err
        items = self.mock_items.get(root_id.lower(), [])
        fname = os.path.basename(relative_path)
        for item in items:
            if item["name"].lower() == fname.lower():
                item["name"] = new_name
                return True, f"Renamed to '{new_name}' (Mocked).", None
        return False, "Item not found", ErrorCode.NOT_FOUND.value

    def delete_path(self, root_id: str, relative_path: str) -> Tuple[bool, str, Optional[str]]:
        ok, resolved_path, root_base, err = path_sandbox.resolve_and_validate(root_id, relative_path)
        if not ok:
            return False, "Validation failed.", err
        items = self.mock_items.get(root_id.lower(), [])
        fname = os.path.basename(relative_path)
        new_items = [i for i in items if i["name"].lower() != fname.lower()]
        self.mock_items[root_id.lower()] = new_items
        return True, f"Item '{fname}' deleted (Mocked).", None


class FilesFeature(BaseFeature):
    def __init__(self, manager: BaseFileManager = None):
        self.manager = manager or WindowsFileManager()

    @property
    def name(self) -> str:
        return "files"

    def register_actions(self, registry) -> None:
        registry.register(
            action_id=AllowedAction.GET_DIRECTORY.value,
            feature=self.name,
            description="Browse items inside an approved logical root directory",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_get_directory,
        )
        registry.register(
            action_id=AllowedAction.GET_FILE_METADATA.value,
            feature=self.name,
            description="Retrieve file or folder metadata",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_get_metadata,
        )
        registry.register(
            action_id=AllowedAction.CREATE_FOLDER.value,
            feature=self.name,
            description="Create new directory in approved root",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_create_folder,
        )
        registry.register(
            action_id=AllowedAction.RENAME_PATH.value,
            feature=self.name,
            description="Rename file or directory in approved root",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_rename_path,
        )
        registry.register(
            action_id=AllowedAction.DELETE_PATH.value,
            feature=self.name,
            description="Delete file or directory in approved root",
            permission_level="ADMIN",
            confirmation_required=True,
            handler=self.handle_delete_path,
        )
        registry.register(
            action_id=AllowedAction.START_UPLOAD.value,
            feature=self.name,
            description="Initialize chunked file upload stream",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_start_upload,
        )
        registry.register(
            action_id=AllowedAction.START_DOWNLOAD.value,
            feature=self.name,
            description="Initialize chunked file download stream",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_start_download,
        )
        registry.register(
            action_id=AllowedAction.CANCEL_TRANSFER.value,
            feature=self.name,
            description="Cancel active file upload or download transfer",
            permission_level="NORMAL",
            confirmation_required=False,
            handler=self.handle_cancel_transfer,
        )

    def handle_get_directory(self, req: ActionRequest) -> ActionResponse:
        root_id = req.parameters.get("root_id", "").strip()
        rel_path = req.parameters.get("relative_path", "").strip()

        ok, items, err_code = self.manager.get_directory(root_id, rel_path)
        roots_info = [
            {"root_id": r["root_id"], "display_name": r["display_name"]}
            for r in path_sandbox.get_approved_roots().values()
        ]

        if not ok:
            return ActionResponse(
                success=False,
                request_id=req.request_id,
                action=req.action,
                message=f"Failed to list directory: {err_code}",
                error_code=err_code,
                data={"roots": roots_info},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        return ActionResponse(
            success=True,
            request_id=req.request_id,
            action=req.action,
            message="Directory contents retrieved successfully",
            data={
                "root_id": root_id,
                "relative_path": rel_path,
                "items": items,
                "roots": roots_info,
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_get_metadata(self, req: ActionRequest) -> ActionResponse:
        root_id = req.parameters.get("root_id", "").strip()
        rel_path = req.parameters.get("relative_path", "").strip()

        ok, meta, err_code = self.manager.get_file_metadata(root_id, rel_path)
        if not ok:
            return ActionResponse(
                success=False,
                request_id=req.request_id,
                action=req.action,
                message=f"Failed to get metadata: {err_code}",
                error_code=err_code,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        return ActionResponse(
            success=True,
            request_id=req.request_id,
            action=req.action,
            message="File metadata retrieved successfully",
            data=meta,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_create_folder(self, req: ActionRequest) -> ActionResponse:
        root_id = req.parameters.get("root_id", "").strip()
        rel_parent = req.parameters.get("relative_parent_path", "").strip()
        fname = req.parameters.get("folder_name", "").strip()

        ok, msg, err_code = self.manager.create_folder(root_id, rel_parent, fname)
        return ActionResponse(
            success=ok,
            request_id=req.request_id,
            action=req.action,
            message=msg,
            error_code=err_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_rename_path(self, req: ActionRequest) -> ActionResponse:
        root_id = req.parameters.get("root_id", "").strip()
        rel_path = req.parameters.get("relative_path", "").strip()
        new_name = req.parameters.get("new_name", "").strip()

        ok, msg, err_code = self.manager.rename_path(root_id, rel_path, new_name)
        return ActionResponse(
            success=ok,
            request_id=req.request_id,
            action=req.action,
            message=msg,
            error_code=err_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_delete_path(self, req: ActionRequest) -> ActionResponse:
        root_id = req.parameters.get("root_id", "").strip()
        rel_path = req.parameters.get("relative_path", "").strip()

        ok, msg, err_code = self.manager.delete_path(root_id, rel_path)
        return ActionResponse(
            success=ok,
            request_id=req.request_id,
            action=req.action,
            message=msg,
            error_code=err_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_start_upload(self, req: ActionRequest) -> ActionResponse:
        root_id = req.parameters.get("root_id", "").strip()
        rel_path = req.parameters.get("relative_path", "").strip()
        total_size = req.parameters.get("total_size", 0)
        file_name = req.parameters.get("file_name", os.path.basename(rel_path) or "upload.tmp")

        ok_val, resolved_path, root_base, err = path_sandbox.resolve_and_validate(root_id, rel_path)
        if not ok_val:
            return ActionResponse(
                success=False,
                request_id=req.request_id,
                action=req.action,
                message=f"Invalid target path: {err}",
                error_code=err,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        ok, session, err_code = transfer_manager.create_upload_session(file_name, resolved_path, total_size)
        return ActionResponse(
            success=ok,
            request_id=req.request_id,
            action=req.action,
            message="Upload session created successfully" if ok else f"Failed to start upload: {err_code}",
            error_code=err_code,
            data={"transfer_id": session.transfer_id, "status": session.status, "tmp_path": session.tmp_path} if ok else None,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_start_download(self, req: ActionRequest) -> ActionResponse:
        root_id = req.parameters.get("root_id", "").strip()
        rel_path = req.parameters.get("relative_path", "").strip()

        ok_val, resolved_path, root_base, err = path_sandbox.resolve_and_validate(root_id, rel_path)
        if not ok_val:
            return ActionResponse(
                success=False,
                request_id=req.request_id,
                action=req.action,
                message=f"Invalid file path: {err}",
                error_code=err,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        if not os.path.exists(resolved_path) or os.path.isdir(resolved_path):
            return ActionResponse(
                success=False,
                request_id=req.request_id,
                action=req.action,
                message="File not found or is a directory.",
                error_code=ErrorCode.NOT_FOUND.value,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        stat = os.stat(resolved_path)
        return ActionResponse(
            success=True,
            request_id=req.request_id,
            action=req.action,
            message="Download stream ready",
            data={"relative_path": rel_path, "size": stat.st_size},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_cancel_transfer(self, req: ActionRequest) -> ActionResponse:
        transfer_id = req.parameters.get("transfer_id", "").strip()

        ok, msg, err_code = transfer_manager.cancel_transfer(transfer_id)
        return ActionResponse(
            success=ok,
            request_id=req.request_id,
            action=req.action,
            message=msg,
            error_code=err_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
