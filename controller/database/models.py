from dataclasses import dataclass
from typing import Optional


@dataclass
class ComputerRecord:
    id: Optional[int]
    agent_id: str
    display_name: str
    ip_address: str
    port: int
    auth_token: Optional[str]
    os_name: str
    agent_version: str
    status: str  # "ONLINE", "OFFLINE"
    last_seen: str
    created_at: str
    updated_at: str


@dataclass
class ActivityRecord:
    id: Optional[int]
    request_id: str
    computer_id: Optional[str]
    computer_name: Optional[str]
    action: str
    status: str  # "SUCCESS", "FAILED", "WARNING"
    message: str
    created_at: str
