import json
import os
from typing import Dict, Any, Optional
from agent.utils.logging_config import logger

ALLOWLIST_FILE = "allowed_apps.json"

DEFAULT_ALLOWLIST = {
    "excel": {
        "app_id": "excel",
        "display_name": "Microsoft Excel",
        "executable_name": "EXCEL.EXE",
        "executable_path": "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
        "enabled": True,
        "manageable": True,
    },
    "word": {
        "app_id": "word",
        "display_name": "Microsoft Word",
        "executable_name": "WINWORD.EXE",
        "executable_path": "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
        "enabled": True,
        "manageable": True,
    },
    "chrome": {
        "app_id": "chrome",
        "display_name": "Google Chrome",
        "executable_name": "chrome.exe",
        "executable_path": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "enabled": True,
        "manageable": True,
    },
    "notepad": {
        "app_id": "notepad",
        "display_name": "Notepad",
        "executable_name": "notepad.exe",
        "executable_path": "C:\\Windows\\notepad.exe",
        "enabled": True,
        "manageable": True,
    },
    "calc": {
        "app_id": "calc",
        "display_name": "Calculator",
        "executable_name": "calc.exe",
        "executable_path": "C:\\Windows\\System32\\calc.exe",
        "enabled": True,
        "manageable": True,
    },
}


class ApplicationAllowlist:
    def __init__(self, file_path: str = ALLOWLIST_FILE):
        self.file_path = file_path
        self.apps: Dict[str, Dict[str, Any]] = {}
        self.load_or_create()

    def load_or_create(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.apps = json.load(f)
                return
            except Exception as e:
                logger.error(f"Failed to load allowed_apps.json: {e}")

        self.apps = DEFAULT_ALLOWLIST.copy()
        self.save()

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.apps, f, indent=2)

    def get_app(self, app_id: str) -> Optional[Dict[str, Any]]:
        return self.apps.get(app_id.lower().strip())

    def get_all_apps(self) -> Dict[str, Dict[str, Any]]:
        return self.apps


app_allowlist = ApplicationAllowlist()
