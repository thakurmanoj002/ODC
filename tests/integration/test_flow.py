import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from shared.models.responses import HealthResponse
from agent.config.settings import AgentSettings
import agent.config.settings as settings_module
from agent.api.server import create_agent_app
from controller.services.agent_client import AgentClient


def test_agent_controller_end_to_end():
    tmp_fd, cfg_path = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)

    agent_settings = AgentSettings(config_path=cfg_path)
    agent_settings.pairing_code = "654321"
    agent_settings.save()
    
    original_settings = settings_module.agent_settings
    settings_module.agent_settings = agent_settings

    app = create_agent_app()
    client = TestClient(app)

    try:
        # Health check
        response = client.get("/health")
        assert response.status_code == 200
        health = HealthResponse.model_validate_json(response.text)
        assert health.status == "online"
        assert health.agent_id == agent_settings.agent_id

        # Pairing
        pair_resp = client.post(
            "/api/pair",
            json={
                "controller_id": "CTRL-INTEG-001",
                "controller_name": "IntegrationTestController",
                "pairing_code": "654321",
            },
        )
        assert pair_resp.status_code == 200
        pair_data = pair_resp.json()
        assert pair_data["success"] is True
        token = pair_data["auth_token"]

        # Protected system info call
        sys_resp = client.get("/api/system-info", headers={"X-Agent-Token": token})
        assert sys_resp.status_code == 200
        sys_data = sys_resp.json()
        assert sys_data["agent_version"] == "1.0.0"

    finally:
        settings_module.agent_settings = original_settings
        if os.path.exists(cfg_path):
            try:
                os.remove(cfg_path)
            except OSError:
                pass
