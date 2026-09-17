import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from shared.constants.protocol import AUTH_HEADER_NAME, AllowedAction, ErrorCode
from agent.config.settings import AgentSettings
import agent.config.settings as settings_module
from agent.core.server import create_agent_app
from agent.features.power.base import BasePowerManager
from agent.features.network.wifi import WindowsWifiManager
from agent.features.power.provider import PowerFeature
from agent.features.network.provider import NetworkFeature
from agent.core.registry import action_registry


class MockWifiManager(WindowsWifiManager):
    def __init__(self, available=True, state="CONNECTED"):
        self.available = available
        self.state = state
        self.ssid = "Office-Test-WiFi"

    def get_wifi_status(self):
        if not self.available:
            return {
                "available": False,
                "state": "UNAVAILABLE",
                "ssid": None,
                "adapter": None,
                "error_code": ErrorCode.WIFI_ADAPTER_NOT_FOUND.value,
            }
        return {
            "available": True,
            "state": self.state,
            "ssid": self.ssid if self.state == "CONNECTED" else None,
            "adapter": "Wi-Fi Test Adapter",
            "error_code": None,
        }

    def set_wifi_state(self, enable: bool):
        if not self.available:
            return False, "Wi-Fi adapter unavailable", ErrorCode.WIFI_ADAPTER_NOT_FOUND.value
        self.state = "CONNECTED" if enable else "DISABLED"
        return True, f"Wi-Fi {'enabled' if enable else 'disabled'} successfully (Mocked).", None


class MockPowerManager(BasePowerManager):
    def __init__(self):
        self.locked = False
        self.restarted = False
        self.shutdown_sent = False

    def lock(self):
        self.locked = True
        return True, "Workstation locked (Mocked).", None

    def restart(self):
        self.restarted = True
        return True, "Restart command sent (Mocked).", None

    def shutdown(self):
        self.shutdown_sent = True
        return True, "Shutdown command sent (Mocked).", None


@pytest.fixture
def test_phase2_agent_env():
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)

    test_settings = AgentSettings(config_path=tmp_path)
    test_settings.pairing_code = "223344"
    test_settings.save()

    original_settings = settings_module.agent_settings
    settings_module.agent_settings = test_settings

    app = create_agent_app()

    # Inject MOCK managers into ActionRegistry so real PC operations are NEVER triggered
    mock_power = MockPowerManager()
    mock_wifi = MockWifiManager()

    power_feat = PowerFeature(manager=mock_power)
    power_feat.register_actions(action_registry)

    net_feat = NetworkFeature(wifi_manager=mock_wifi)
    net_feat.register_actions(action_registry)

    client = TestClient(app)

    yield client, test_settings, mock_wifi, mock_power

    settings_module.agent_settings = original_settings
    if os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def test_wifi_status_action(test_phase2_agent_env):
    client, settings, mock_wifi, _ = test_phase2_agent_env

    pair_resp = client.post("/api/v1/pair", json={"controller_id": "C1", "controller_name": "C1", "pairing_code": "223344"})
    token = pair_resp.json()["auth_token"]
    headers = {AUTH_HEADER_NAME: token}

    resp = client.post("/api/v1/action", json={"request_id": "r1", "action": AllowedAction.WIFI_STATUS.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["state"] == "CONNECTED"


def test_wifi_on_off_actions(test_phase2_agent_env):
    client, settings, mock_wifi, _ = test_phase2_agent_env

    pair_resp = client.post("/api/v1/pair", json={"controller_id": "C1", "controller_name": "C1", "pairing_code": "223344"})
    token = pair_resp.json()["auth_token"]
    headers = {AUTH_HEADER_NAME: token}

    # Turn OFF
    resp_off = client.post("/api/v1/action", json={"request_id": "r2", "action": AllowedAction.WIFI_OFF.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert resp_off.status_code == 200
    assert resp_off.json()["success"] is True
    assert mock_wifi.state == "DISABLED"

    # Turn ON
    resp_on = client.post("/api/v1/action", json={"request_id": "r3", "action": AllowedAction.WIFI_ON.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert resp_on.status_code == 200
    assert resp_on.json()["success"] is True
    assert mock_wifi.state == "CONNECTED"


def test_power_actions(test_phase2_agent_env):
    client, settings, _, mock_power = test_phase2_agent_env

    pair_resp = client.post("/api/v1/pair", json={"controller_id": "C1", "controller_name": "C1", "pairing_code": "223344"})
    token = pair_resp.json()["auth_token"]
    headers = {AUTH_HEADER_NAME: token}

    # Lock PC (Mocked)
    resp_lock = client.post("/api/v1/action", json={"request_id": "r4", "action": AllowedAction.LOCK_PC.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert resp_lock.status_code == 200
    assert resp_lock.json()["success"] is True
    assert mock_power.locked is True

    # Restart PC (Mocked)
    resp_re = client.post("/api/v1/action", json={"request_id": "r5", "action": AllowedAction.RESTART_PC.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert resp_re.status_code == 200
    assert resp_re.json()["success"] is True
    assert mock_power.restarted is True

    # Shutdown PC (Mocked)
    resp_sd = client.post("/api/v1/action", json={"request_id": "r6", "action": AllowedAction.SHUTDOWN_PC.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert resp_sd.status_code == 200
    assert resp_sd.json()["success"] is True
    assert mock_power.shutdown_sent is True
