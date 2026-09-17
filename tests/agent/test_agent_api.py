import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from shared.constants.protocol import AUTH_HEADER_NAME, AllowedAction, ErrorCode
from agent.config.settings import AgentSettings
import agent.config.settings as settings_module
from agent.api.server import create_agent_app


@pytest.fixture
def test_agent_env():
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    test_settings = AgentSettings(config_path=tmp_path)
    test_settings.pairing_code = "123456"
    test_settings.save()
    
    original_settings = settings_module.agent_settings
    settings_module.agent_settings = test_settings

    app = create_agent_app()
    client = TestClient(app)

    yield client, test_settings

    settings_module.agent_settings = original_settings
    if os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def test_health_endpoint(test_agent_env):
    client, settings = test_agent_env
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["agent_id"] == settings.agent_id


def test_unauthenticated_request_rejected(test_agent_env):
    client, settings = test_agent_env
    # Unpaired / no header request should be 401
    response = client.get("/api/system-info")
    assert response.status_code == 401


def test_pairing_flow(test_agent_env):
    client, settings = test_agent_env

    # 1. Incorrect code
    bad_pair = client.post(
        "/api/pair",
        json={
            "controller_id": "CTRL-001",
            "controller_name": "TestController",
            "pairing_code": "000000",
        },
    )
    assert bad_pair.status_code == 200
    assert bad_pair.json()["success"] is False

    # 2. Correct code
    good_pair = client.post(
        "/api/pair",
        json={
            "controller_id": "CTRL-001",
            "controller_name": "TestController",
            "pairing_code": "123456",
        },
    )
    assert good_pair.status_code == 200
    pair_data = good_pair.json()
    assert pair_data["success"] is True
    assert pair_data["auth_token"] is not None

    token = pair_data["auth_token"]

    # 3. Access protected system-info endpoint
    headers = {AUTH_HEADER_NAME: token}
    sys_resp = client.get("/api/system-info", headers=headers)
    assert sys_resp.status_code == 200
    sys_data = sys_resp.json()
    assert "cpu_usage" in sys_data
    assert "ram_usage" in sys_data


def test_action_endpoint(test_agent_env):
    client, settings = test_agent_env

    # Pair first
    good_pair = client.post(
        "/api/pair",
        json={
            "controller_id": "CTRL-001",
            "controller_name": "TestController",
            "pairing_code": "123456",
        },
    )
    token = good_pair.json()["auth_token"]
    assert token is not None
    headers = {AUTH_HEADER_NAME: token}

    # Test GET_STATUS action
    action_req = {
        "request_id": "req-001",
        "action": AllowedAction.GET_STATUS.value,
        "timestamp": "2026-09-17T12:00:00Z",
    }
    resp = client.post("/api/action", json=action_req, headers=headers)
    assert resp.status_code == 200
    act_data = resp.json()
    assert act_data["success"] is True
    assert act_data["action"] == AllowedAction.GET_STATUS.value

    # Test unsupported action
    unsupported_req = {
        "request_id": "req-002",
        "action": "NON_EXISTENT_ACTION",
        "timestamp": "2026-09-17T12:00:00Z",
    }
    resp2 = client.post("/api/action", json=unsupported_req, headers=headers)
    assert resp2.status_code == 200
    act_data2 = resp2.json()
    assert act_data2["success"] is False
    assert act_data2["error_code"] == ErrorCode.INVALID_ACTION.value
