from fastapi import Header, HTTPException, status
from shared.constants.protocol import AUTH_HEADER_NAME
import agent.config.settings as settings_module
from agent.utils.logging_config import logger


def verify_auth_token(x_agent_token: str = Header(None, alias=AUTH_HEADER_NAME)):
    s = settings_module.agent_settings
    if s.pairing_status != "PAIRED" or not s.auth_token:
        logger.warning("Unauthenticated request received: Agent is not paired yet")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent is not paired with a trusted controller",
        )

    if not x_agent_token or x_agent_token != s.auth_token:
        logger.warning("Unauthenticated request rejected: Invalid or missing token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
        )
    return True
