import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from shared.constants.protocol import AUTH_HEADER_NAME, AllowedAction, ErrorCode
from agent.config.settings import AgentSettings
import agent.config.settings as settings_module
from agent.core.server import create_agent_app
from agent.features.applications.provider import ApplicationFeature, MockApplicationManager
from agent.core.registry import action_registry


@pytest.fixture
def test_phase3_agent_env():
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)

    test_settings = AgentSettings(config_path=tmp_path)
    test_settings.pairing_code = "334455"
    test_settings.safe_mode = True  # Mandatory safe_mode guard
    test_settings.save()

    original_settings = settings_module.agent_settings
    settings_module.agent_settings = test_settings

    app = create_agent_app()

    # Inject MockApplicationManager for 100% safe testing
    mock_app_mgr = MockApplicationManager()
    app_feat = ApplicationFeature(manager=mock_app_mgr)
    app_feat.register_actions(action_registry)

    client = TestClient(app)

    yield client, test_settings, mock_app_mgr

    settings_module.agent_settings = original_settings
    if os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def test_get_running_applications(test_phase3_agent_env):
    client, settings, mock_mgr = test_phase3_agent_env

    pair_resp = client.post("/api/v1/pair", json={"controller_id": "C1", "controller_name": "C1", "pairing_code": "334455"})
    token = pair_resp.json()["auth_token"]
    headers = {AUTH_HEADER_NAME: token}

    resp = client.post("/api/v1/action", json={"request_id": "r1", "action": AllowedAction.GET_RUNNING_APPLICATIONS.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "running_apps" in data["data"]
    assert len(data["data"]["running_apps"]) > 0
    assert data["data"]["running_apps"][0]["app_id"] == "excel"


def test_start_stop_allowed_app(test_phase3_agent_env):
    client, settings, mock_mgr = test_phase3_agent_env

    pair_resp = client.post("/api/v1/pair", json={"controller_id": "C1", "controller_name": "C1", "pairing_code": "334455"})
    token = pair_resp.json()["auth_token"]
    headers = {AUTH_HEADER_NAME: token}

    # Start notepad (Mocked)
    start_resp = client.post(
        "/api/v1/action",
        json={"request_id": "r2", "action": AllowedAction.START_ALLOWED_APP.value, "parameters": {"app_id": "notepad"}, "timestamp": "2026-09-17T12:00:00Z"},
        headers=headers,
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["success"] is True

    # Stop excel (Mocked)
    stop_resp = client.post(
        "/api/v1/action",
        json={"request_id": "r3", "action": AllowedAction.STOP_ALLOWED_APP.value, "parameters": {"app_id": "excel"}, "timestamp": "2026-09-17T12:00:00Z"},
        headers=headers,
    )
    assert stop_resp.status_code == 200
    assert stop_resp.json()["success"] is True


def test_invalid_and_injection_app_id_rejection(test_phase3_agent_env):
    client, settings, mock_mgr = test_phase3_agent_env

    pair_resp = client.post("/api/v1/pair", json={"controller_id": "C1", "controller_name": "C1", "pairing_code": "334455"})
    token = pair_resp.json()["auth_token"]
    headers = {AUTH_HEADER_NAME: token}

    # Test unknown app_id
    bad_id = client.post(
        "/api/v1/action",
        json={"request_id": "r4", "action": AllowedAction.START_ALLOWED_APP.value, "parameters": {"app_id": "malicious_app"}, "timestamp": "2026-09-17T12:00:00Z"},
        headers=headers,
    )
    assert bad_id.status_code == 200
    assert bad_id.json()["success"] is False
    assert bad_id.json()["error_code"] == ErrorCode.APP_NOT_ALLOWED.value

    # Test path injection attempt in app_id
    path_inj = client.post(
        "/api/v1/action",
        json={"request_id": "r5", "action": AllowedAction.START_ALLOWED_APP.value, "parameters": {"app_id": "C:\\Windows\\System32\\cmd.exe"}, "timestamp": "2026-09-17T12:00:00Z"},
        headers=headers,
    )
    assert path_inj.status_code == 200
    assert path_inj.json()["success"] is False
    assert path_inj.json()["error_code"] == ErrorCode.APP_NOT_ALLOWED.value


def test_safe_mode_blocking():
    # Test real WindowsApplicationManager with SAFE_MODE = True
    from agent.features.applications.provider import WindowsApplicationManager
    import agent.config.settings as settings_mod

    settings_mod.agent_settings.safe_mode = True
    win_mgr = WindowsApplicationManager()

    success, msg, err_code = win_mgr.start_allowed_application("notepad")
    assert success is False
    assert err_code == ErrorCode.SAFE_MODE_BLOCKED.value

    success_stop, msg_stop, err_code_stop = win_mgr.stop_allowed_application("notepad")
    assert success_stop is False
    assert err_code_stop == ErrorCode.SAFE_MODE_BLOCKED.value
