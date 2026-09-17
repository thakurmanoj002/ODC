from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from shared.models.requests import PairRequest, ActionRequest
from shared.models.responses import (
    HealthResponse,
    PairResponse,
    SystemInfoResponse,
    NetworkInfoResponse,
    ActionResponse,
    DiscoveryResponse,
)
from shared.constants.protocol import API_V1_PREFIX, PROTOCOL_VERSION
import agent.config.settings as settings_module
from agent.security.pairing import verify_and_pair
from agent.security.authentication import verify_auth_token
from agent.core.registry import action_registry
from agent.core.capabilities import capability_manager
from agent.features.system.provider import WindowsSystemInfoProvider
from agent.features.network.provider import WindowsNetworkManager
from agent.utils.logging_config import logger

router = APIRouter()
sys_provider = WindowsSystemInfoProvider()
net_manager = WindowsNetworkManager()


# --- Health Endpoints ---
@router.get("/health", response_model=HealthResponse)
@router.get(f"{API_V1_PREFIX}/health", response_model=HealthResponse)
def health_check():
    s = settings_module.agent_settings
    return HealthResponse(
        status="online",
        agent_id=s.agent_id,
        computer_name=s.computer_name,
        agent_version=s.agent_version,
        protocol_version=PROTOCOL_VERSION,
        capabilities=capability_manager.get_capabilities(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# --- Pairing Endpoints ---
@router.post("/api/pair", response_model=PairResponse)
@router.post(f"{API_V1_PREFIX}/pair", response_model=PairResponse)
def pair_agent(req: PairRequest):
    return verify_and_pair(req)


# --- Agent Info Endpoints ---
@router.get("/api/agent-info", response_model=DiscoveryResponse, dependencies=[Depends(verify_auth_token)])
@router.get(f"{API_V1_PREFIX}/agent-info", response_model=DiscoveryResponse, dependencies=[Depends(verify_auth_token)])
def get_agent_info():
    s = settings_module.agent_settings
    return DiscoveryResponse(
        agent_id=s.agent_id,
        computer_name=s.computer_name,
        ip_address=net_manager.get_local_ip(),
        port=s.server_port,
        agent_version=s.agent_version,
        pairing_status=s.pairing_status,
        capabilities=capability_manager.get_capabilities(),
    )


# --- Capability Discovery Endpoints ---
@router.get("/api/capabilities", response_model=List[str], dependencies=[Depends(verify_auth_token)])
@router.get(f"{API_V1_PREFIX}/capabilities", response_model=List[str], dependencies=[Depends(verify_auth_token)])
def get_capabilities():
    return capability_manager.get_capabilities()


# --- Telemetry Endpoints ---
@router.get("/api/system-info", response_model=SystemInfoResponse, dependencies=[Depends(verify_auth_token)])
@router.get(f"{API_V1_PREFIX}/system-info", response_model=SystemInfoResponse, dependencies=[Depends(verify_auth_token)])
def fetch_system_info():
    return sys_provider.get_system_info()


@router.get("/api/network-info", response_model=NetworkInfoResponse, dependencies=[Depends(verify_auth_token)])
@router.get(f"{API_V1_PREFIX}/network-info", response_model=NetworkInfoResponse, dependencies=[Depends(verify_auth_token)])
def fetch_network_info():
    return net_manager.get_network_info()


# --- Centralized Action Endpoint ---
@router.post("/api/action", response_model=ActionResponse, dependencies=[Depends(verify_auth_token)])
@router.post(f"{API_V1_PREFIX}/action", response_model=ActionResponse, dependencies=[Depends(verify_auth_token)])
def execute_action(req: ActionRequest):
    logger.info(f"Received action request: {req.action} (req_id={req.request_id})")
    return action_registry.execute(req)
