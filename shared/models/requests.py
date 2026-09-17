from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class PairRequest(BaseModel):
    controller_id: str = Field(..., description="Unique ID of the requesting Controller")
    controller_name: str = Field(..., description="Display name of the Controller")
    pairing_code: str = Field(..., description="6-digit pairing code entered by user")


class ActionRequest(BaseModel):
    request_id: str = Field(..., description="Unique UUID for request tracing and replay prevention")
    action: str = Field(..., description="Allowlisted action name")
    timestamp: str = Field(..., description="ISO 8601 string or Unix timestamp")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action specific parameters")
