import json
import os
import socket
import uuid

CONFIG_FILE = "controller_config.json"


class ControllerSettings:
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.controller_id: str = ""
        self.controller_name: str = ""
        self.refresh_interval_sec: int = 5
        self.discovery_enabled: bool = True
        self.theme: str = "Light"

        self.load_or_create()

    def load_or_create(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.controller_id = data.get("controller_id", f"CTRL-{uuid.uuid4().hex[:6].upper()}")
                self.controller_name = data.get("controller_name", f"{socket.gethostname()}-Controller")
                self.refresh_interval_sec = data.get("refresh_interval_sec", 5)
                self.discovery_enabled = data.get("discovery_enabled", True)
                self.theme = data.get("theme", "Light")
                return
            except Exception:
                pass

        self.controller_id = f"CTRL-{uuid.uuid4().hex[:6].upper()}"
        self.controller_name = f"{socket.gethostname()}-Controller"
        self.refresh_interval_sec = 5
        self.discovery_enabled = True
        self.theme = "Light"
        self.save()

    def save(self):
        data = {
            "controller_id": self.controller_id,
            "controller_name": self.controller_name,
            "refresh_interval_sec": self.refresh_interval_sec,
            "discovery_enabled": self.discovery_enabled,
            "theme": self.theme,
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


controller_settings = ControllerSettings()
