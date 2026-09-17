from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class HealthResponse(BaseModel):
    status: str = Field("online", description="Agent health status")
    agent_id: str = Field(..., description="Unique Agent identifier")
    computer_name: str = Field(..., description="Host computer display name")
    agent_version: str = Field("1.0.0", description="Agent software version")
    protocol_version: str = Field("1.0.0", description="Protocol version")
    capabilities: List[str] = Field(default_factory=list, description="Supported agent capabilities")
    timestamp: str = Field(..., description="Current ISO 8601 timestamp")


class PairResponse(BaseModel):
    success: bool = Field(..., description="True if pairing succeeded")
    agent_id: str = Field(..., description="Agent ID")
    auth_token: Optional[str] = Field(None, description="Secret token issued to Controller upon success")
    message: str = Field(..., description="Status or error message")


class SystemInfoResponse(BaseModel):
    computer_name: str
    os_name: str
    os_version: str
    cpu_usage: float
    ram_usage: float
    total_ram_gb: float
    used_ram_gb: float
    disk_usage: float
    uptime_seconds: float
    agent_version: str


class NetworkInfoResponse(BaseModel):
    local_ip: str
    hostname: str
    connection_info: str
    network_state: str


class ActionResponse(BaseModel):
    success: bool
    request_id: str
    action: str
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    timestamp: str = ""


class DiscoveryResponse(BaseModel):
    agent_id: str
    computer_name: str
    ip_address: str
    port: int
    agent_version: str
    pairing_status: str
    capabilities: List[str] = Field(default_factory=list)
