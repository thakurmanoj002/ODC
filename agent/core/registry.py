from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime, timezone
from shared.models.requests import ActionRequest
from shared.models.responses import ActionResponse
from shared.constants.protocol import ErrorCode
from agent.utils.logging_config import logger


@dataclass
class ActionMetadata:
    action_id: str
    feature: str
    description: str
    permission_level: str  # e.g., "NORMAL", "ADMIN"
    confirmation_required: bool
    handler: Callable[[ActionRequest], ActionResponse]
    parameters_schema: Optional[Dict[str, Any]] = None


class ActionRegistry:
    def __init__(self):
        self._actions: Dict[str, ActionMetadata] = {}

    def register(
        self,
        action_id: str,
        feature: str,
        description: str,
        permission_level: str,
        confirmation_required: bool,
        handler: Callable[[ActionRequest], ActionResponse],
        parameters_schema: Optional[Dict[str, Any]] = None,
    ):
        if action_id in self._actions:
            logger.warning(f"Action '{action_id}' is being re-registered!")
        
        meta = ActionMetadata(
            action_id=action_id,
            feature=feature,
            description=description,
            permission_level=permission_level,
            confirmation_required=confirmation_required,
            handler=handler,
            parameters_schema=parameters_schema,
        )
        self._actions[action_id] = meta
        logger.info(f"Registered action: '{action_id}' (feature: {feature})")

    def get_capabilities(self) -> List[str]:
        """Return list of active action IDs supported by the Agent."""
        return list(self._actions.keys())

    def get_action(self, action_id: str) -> Optional[ActionMetadata]:
        return self._actions.get(action_id)

    def execute(self, req: ActionRequest) -> ActionResponse:
        action_meta = self._actions.get(req.action)
        if not action_meta:
            logger.warning(f"Rejected unknown action: '{req.action}' (req_id={req.request_id})")
            return ActionResponse(
                success=False,
                request_id=req.request_id,
                action=req.action,
                message=f"Action '{req.action}' is not registered or supported by this Agent.",
                error_code=ErrorCode.INVALID_ACTION.value,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        try:
            return action_meta.handler(req)
        except Exception as e:
            logger.error(f"Error executing handler for '{req.action}': {e}", exc_info=True)
            return ActionResponse(
                success=False,
                request_id=req.request_id,
                action=req.action,
                message=f"Internal execution error: {str(e)}",
                error_code=ErrorCode.EXECUTION_FAILED.value,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )


# Global ActionRegistry Singleton
action_registry = ActionRegistry()
