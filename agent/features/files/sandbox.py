import os
from typing import Dict, Any, Tuple, Optional
from shared.constants.protocol import ErrorCode
from agent.utils.logging_config import logger

PROTECTED_DIRECTORIES = {
    r"c:\windows",
    r"c:\program files",
    r"c:\program files (x86)",
    r"c:\windowsapps",
    r"c:\system volume information",
    r"c:\$recycle.bin",
    r"c:\recovery",
}

DEFAULT_APPROVED_ROOTS = {
    "shared": {
        "root_id": "shared",
        "display_name": "Shared Documents",
        "path": os.path.abspath(os.path.join(os.getcwd(), "test_sandbox", "OfficeShared")),
        "enabled": True,
    },
    "documents": {
        "root_id": "documents",
        "display_name": "Company Documents",
        "path": os.path.abspath(os.path.join(os.getcwd(), "test_sandbox", "OfficeDocuments")),
        "enabled": True,
    },
}


class PathSandbox:
    def __init__(self, roots: Optional[Dict[str, Dict[str, Any]]] = None):
        self.roots = roots or DEFAULT_APPROVED_ROOTS.copy()
        self._ensure_sandbox_dirs()

    def _ensure_sandbox_dirs(self):
        for root_info in self.roots.values():
            rpath = root_info.get("path")
            if rpath and not os.path.exists(rpath):
                try:
                    os.makedirs(rpath, exist_ok=True)
                except Exception:
                    pass

    def get_approved_roots(self) -> Dict[str, Dict[str, Any]]:
        return self.roots

    def resolve_and_validate(self, root_id: str, relative_path: str = "") -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Validates root_id and relative_path against traversal and protected OS folders.
        Returns: (success, resolved_absolute_path, root_base_path, error_code)
        """
        root_id_clean = (root_id or "").lower().strip()
        root_info = self.roots.get(root_id_clean)

        if not root_info or not root_info.get("enabled", True):
            logger.warning(f"PathSandbox: Rejected unknown or disabled root_id '{root_id}'")
            return False, None, None, ErrorCode.ROOT_NOT_FOUND.value

        root_path = os.path.abspath(root_info["path"])

        # Sanitize relative path
        rel_clean = (relative_path or "").strip().lstrip("/\\")

        # Explicit traversal check
        if ".." in rel_clean.split("/") or ".." in rel_clean.split("\\"):
            logger.warning(f"PathSandbox: Path traversal attempt detected in relative_path '{relative_path}'")
            return False, None, root_path, ErrorCode.PATH_TRAVERSAL_DETECTED.value

        # Resolve full path
        resolved_path = os.path.abspath(os.path.join(root_path, rel_clean))

        # Commonpath check to prevent escaping root directory boundary
        try:
            if os.path.commonpath([resolved_path, root_path]) != root_path:
                logger.warning(f"PathSandbox: Resolved path '{resolved_path}' escapes root '{root_path}'")
                return False, None, root_path, ErrorCode.PATH_TRAVERSAL_DETECTED.value
        except Exception:
            return False, None, root_path, ErrorCode.PATH_TRAVERSAL_DETECTED.value

        # Protected OS directory check
        resolved_lower = resolved_path.lower()
        for protected in PROTECTED_DIRECTORIES:
            if resolved_lower == protected or resolved_lower.startswith(protected + os.sep):
                logger.warning(f"PathSandbox: Access denied to protected OS directory '{resolved_path}'")
                return False, None, root_path, ErrorCode.PROTECTED_DIRECTORY.value

        return True, resolved_path, root_path, None


path_sandbox = PathSandbox()
