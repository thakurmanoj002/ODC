from typing import List
from agent.core.registry import action_registry
from agent.features.system.provider import SystemFeature
from agent.features.network.provider import NetworkFeature
from agent.features.power.provider import PowerFeature
from agent.features.applications.provider import ApplicationFeature
from agent.features.files.provider import FilesFeature
from agent.utils.logging_config import logger


class CapabilityManager:
    def __init__(self):
        self.features = []

    def register_default_features(self):
        """Initialize and register default agent feature modules."""
        self.features.clear()

        sys_feat = SystemFeature()
        sys_feat.register_actions(action_registry)
        self.features.append(sys_feat)

        net_feat = NetworkFeature()
        net_feat.register_actions(action_registry)
        self.features.append(net_feat)

        power_feat = PowerFeature()
        power_feat.register_actions(action_registry)
        self.features.append(power_feat)

        app_feat = ApplicationFeature()
        app_feat.register_actions(action_registry)
        self.features.append(app_feat)

        files_feat = FilesFeature()
        files_feat.register_actions(action_registry)
        self.features.append(files_feat)

        logger.info(
            f"Initialized {len(self.features)} feature modules. Active capabilities: {action_registry.get_capabilities()}"
        )

    def get_capabilities(self) -> List[str]:
        return action_registry.get_capabilities()


capability_manager = CapabilityManager()
