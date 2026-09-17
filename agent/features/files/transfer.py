import os
import shutil
import uuid
from typing import Dict, Any, Tuple, Optional
from shared.constants.protocol import ErrorCode
from agent.utils.logging_config import logger

MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_DOWNLOAD_SIZE = 500 * 1024 * 1024  # 500 MB


class TransferSession:
    def __init__(self, transfer_id: str, transfer_type: str, file_name: str, target_path: str):
        self.transfer_id = transfer_id
        self.transfer_type = transfer_type  # "UPLOAD" or "DOWNLOAD"
        self.file_name = file_name
        self.target_path = target_path
        self.tmp_path = f"{target_path}.tmp" if transfer_type == "UPLOAD" else target_path
        self.status = "QUEUED"  # QUEUED, TRANSFERRING, COMPLETED, FAILED, CANCELLED
        self.transferred_bytes = 0
        self.total_bytes = 0


class TransferManager:
    def __init__(self):
        self.active_transfers: Dict[str, TransferSession] = {}

    def create_upload_session(self, file_name: str, target_path: str, total_bytes: int) -> Tuple[bool, Optional[TransferSession], Optional[str]]:
        if total_bytes > MAX_UPLOAD_SIZE:
            return False, None, ErrorCode.FILE_TOO_LARGE.value

        if os.path.exists(target_path):
            return False, None, ErrorCode.FILE_EXISTS.value

        transfer_id = f"tx-{uuid.uuid4().hex[:10]}"
        session = TransferSession(transfer_id, "UPLOAD", file_name, target_path)
        session.total_bytes = total_bytes
        self.active_transfers[transfer_id] = session
        logger.info(f"Created upload transfer session '{transfer_id}' for file '{file_name}'")
        return True, session, None

    def cancel_transfer(self, transfer_id: str) -> Tuple[bool, str, Optional[str]]:
        session = self.active_transfers.get(transfer_id)
        if not session:
            return False, f"Transfer session '{transfer_id}' not found.", ErrorCode.NOT_FOUND.value

        session.status = "CANCELLED"
        if session.transfer_type == "UPLOAD" and os.path.exists(session.tmp_path):
            try:
                os.remove(session.tmp_path)
            except Exception as e:
                logger.error(f"Failed to clean up cancelled temp upload file: {e}")

        logger.info(f"Cancelled transfer session '{transfer_id}'")
        return True, f"Transfer '{session.file_name}' cancelled successfully.", None

    def complete_upload(self, transfer_id: str) -> Tuple[bool, str, Optional[str]]:
        session = self.active_transfers.get(transfer_id)
        if not session:
            return False, "Session not found", ErrorCode.NOT_FOUND.value

        if session.status == "CANCELLED":
            return False, "Transfer was cancelled", ErrorCode.TRANSFER_CANCELLED.value

        try:
            if os.path.exists(session.tmp_path):
                shutil.move(session.tmp_path, session.target_path)
                session.status = "COMPLETED"
                logger.info(f"Upload complete: {session.target_path}")
                return True, f"File '{session.file_name}' uploaded successfully.", None
            else:
                return False, "Temporary upload file not found.", ErrorCode.TRANSFER_FAILED.value
        except Exception as e:
            logger.error(f"Error finalizing upload '{transfer_id}': {e}")
            return False, f"Failed to finalize upload: {str(e)}", ErrorCode.TRANSFER_FAILED.value


transfer_manager = TransferManager()
