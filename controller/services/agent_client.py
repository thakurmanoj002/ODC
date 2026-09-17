import httpx
from typing import Optional
from shared.constants.protocol import AUTH_HEADER_NAME
from shared.models.requests import PairRequest, ActionRequest
from shared.models.responses import (
    HealthResponse,
    PairResponse,
    SystemInfoResponse,
    NetworkInfoResponse,
    ActionResponse,
)
from controller.utils.logging_config import logger


class AgentClient:
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    def _get_url(self, ip: str, port: int, path: str) -> str:
        return f"http://{ip}:{port}{path}"

    def check_health(self, ip: str, port: int) -> Optional[HealthResponse]:
        url = self._get_url(ip, port, "/health")
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    return HealthResponse.model_validate_json(resp.text)
        except Exception as e:
            logger.debug(f"Health check failed for {ip}:{port}: {e}")
        return None

    def pair(
        self, ip: str, port: int, controller_id: str, controller_name: str, pairing_code: str
    ) -> PairResponse:
        url = self._get_url(ip, port, "/api/pair")
        req_payload = PairRequest(
            controller_id=controller_id,
            controller_name=controller_name,
            pairing_code=pairing_code,
        )
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=req_payload.model_dump())
                return PairResponse.model_validate_json(resp.text)
        except Exception as e:
            logger.error(f"Pairing request failed for {ip}:{port}: {e}")
            return PairResponse(
                success=False,
                agent_id="",
                auth_token=None,
                message=f"Network error during pairing: {str(e)}",
            )

    def get_system_info(self, ip: str, port: int, auth_token: str) -> Optional[SystemInfoResponse]:
        url = self._get_url(ip, port, "/api/system-info")
        headers = {AUTH_HEADER_NAME: auth_token}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    return SystemInfoResponse.model_validate_json(resp.text)
                else:
                    logger.warning(
                        f"System info request rejected by {ip}:{port} (HTTP {resp.status_code})"
                    )
        except Exception as e:
            logger.error(f"Failed to fetch system info from {ip}:{port}: {e}")
        return None

    def get_network_info(self, ip: str, port: int, auth_token: str) -> Optional[NetworkInfoResponse]:
        url = self._get_url(ip, port, "/api/network-info")
        headers = {AUTH_HEADER_NAME: auth_token}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    return NetworkInfoResponse.model_validate_json(resp.text)
        except Exception as e:
            logger.error(f"Failed to fetch network info from {ip}:{port}: {e}")
        return None

    def send_action(
        self, ip: str, port: int, auth_token: str, action_req: ActionRequest
    ) -> ActionResponse:
        url = self._get_url(ip, port, "/api/action")
        headers = {AUTH_HEADER_NAME: auth_token}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=action_req.model_dump(), headers=headers)
                if resp.status_code == 200:
                    return ActionResponse.model_validate_json(resp.text)
                else:
                    return ActionResponse(
                        success=False,
                        request_id=action_req.request_id,
                        action=action_req.action,
                        message=f"Request failed with status code {resp.status_code}",
                        error_code="UNAUTHORIZED" if resp.status_code == 401 else "EXECUTION_FAILED",
                    )
        except Exception as e:
            logger.error(f"Action execution error on {ip}:{port}: {e}")
            return ActionResponse(
                success=False,
                request_id=action_req.request_id,
                action=action_req.action,
                message=f"Network error: {str(e)}",
                error_code="OFFLINE",
            )


agent_client = AgentClient()
