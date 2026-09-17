from shared.models.requests import PairRequest
from shared.models.responses import PairResponse
import agent.config.settings as settings_module
from agent.utils.logging_config import logger


def verify_and_pair(req: PairRequest) -> PairResponse:
    s = settings_module.agent_settings
    if req.pairing_code != s.pairing_code:
        logger.warning(
            f"Failed pairing attempt from {req.controller_id} ({req.controller_name}): Invalid pairing code"
        )
        return PairResponse(
            success=False,
            agent_id=s.agent_id,
            auth_token=None,
            message="Invalid pairing code provided",
        )

    auth_token = s.pair_with(req.controller_id)
    return PairResponse(
        success=True,
        agent_id=s.agent_id,
        auth_token=auth_token,
        message="Agent successfully paired with Controller",
    )
