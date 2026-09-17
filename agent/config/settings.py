import json
import os
import random
import socket
import uuid
from typing import Optional
from agent.utils.logging_config import logger

CONFIG_FILE = "agent_config.json"


class AgentSettings:
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.agent_id: str = ""
        self.computer_name: str = ""
        self.installation_id: str = ""
        self.server_port: int = 8765
        self.pairing_code: str = ""
        self.pairing_status: str = "UNPAIRED"  # UNPAIRED or PAIRED
        self.auth_token: Optional[str] = None
        self.trusted_controller_id: Optional[str] = None
        self.agent_version: str = "1.0.0"
        self.safe_mode: bool = False  # Real machine execution enabled!

        self.load_or_create()

    def load_or_create(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.agent_id = data.get("agent_id", "")
                self.computer_name = data.get("computer_name", socket.gethostname())
                self.installation_id = data.get("installation_id", str(uuid.uuid4()))
                self.server_port = data.get("server_port", 8765)
                self.pairing_code = data.get("pairing_code", self._generate_pairing_code())
                self.pairing_status = data.get("pairing_status", "UNPAIRED")
                self.auth_token = data.get("auth_token")
                self.trusted_controller_id = data.get("trusted_controller_id")
                self.agent_version = data.get("agent_version", "1.0.0")
                self.safe_mode = data.get("safe_mode", False)
                logger.info(f"Loaded existing agent config: {self.agent_id} (safe_mode={self.safe_mode})")
                return
            except Exception as e:
                logger.error(f"Failed to load agent config, creating new: {e}")

        # First run initialization
        self.agent_id = f"AGENT-{uuid.uuid4().hex[:6].upper()}"
        self.computer_name = socket.gethostname()
        self.installation_id = str(uuid.uuid4())
        self.server_port = 8765
        self.pairing_code = self._generate_pairing_code()
        self.pairing_status = "UNPAIRED"
        self.auth_token = None
        self.trusted_controller_id = None
        self.agent_version = "1.0.0"
        self.safe_mode = False
        self.save()
        logger.info(f"Initialized new agent config: {self.agent_id} (safe_mode=False)")

    def _generate_pairing_code(self) -> str:
        return f"{random.randint(100000, 999999)}"

    def save(self):
        data = {
            "agent_id": self.agent_id,
            "computer_name": self.computer_name,
            "installation_id": self.installation_id,
            "server_port": self.server_port,
            "pairing_code": self.pairing_code,
            "pairing_status": self.pairing_status,
            "auth_token": self.auth_token,
            "trusted_controller_id": self.trusted_controller_id,
            "agent_version": self.agent_version,
            "safe_mode": self.safe_mode,
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def pair_with(self, controller_id: str) -> str:
        new_token = f"tok_{uuid.uuid4().hex}"
        self.auth_token = new_token
        self.trusted_controller_id = controller_id
        self.pairing_status = "PAIRED"
        self.save()
        logger.info(f"Successfully paired with Controller: {controller_id}")
        return new_token


agent_settings = AgentSettings()
