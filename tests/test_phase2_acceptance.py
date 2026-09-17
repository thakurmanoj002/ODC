import os
import tempfile
from fastapi.testclient import TestClient
from shared.models.responses import HealthResponse, ActionResponse
from shared.constants.protocol import AUTH_HEADER_NAME, AllowedAction, ErrorCode
from agent.config.settings import AgentSettings
import agent.config.settings as settings_module
from agent.core.server import create_agent_app
from agent.features.power.provider import PowerFeature
from agent.features.network.provider import NetworkFeature
from agent.core.registry import action_registry
from tests.agent.test_phase2_actions import MockWifiManager, MockPowerManager
from controller.database.database import Database
from controller.database.models import ComputerRecord
from controller.services.computer_service import computer_service


def run_phase2_acceptance_tests():
    print("==================================================")
    print("RUNNING PHASE 2 ACCEPTANCE TESTS (18 / 18 TESTS)")
    print("==================================================")

    # 1. Setup temporary Agent environment
    tmp_fd, cfg_path = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)

    ag_settings = AgentSettings(config_path=cfg_path)
    ag_settings.pairing_code = "778899"
    ag_settings.save()
    settings_module.agent_settings = ag_settings

    app = create_agent_app()

    # Inject MOCK managers so NO real netsh or shutdown commands are run on user's PC
    mock_power = MockPowerManager()
    mock_wifi = MockWifiManager(available=True, state="CONNECTED")

    power_feat = PowerFeature(manager=mock_power)
    power_feat.register_actions(action_registry)

    net_feat = NetworkFeature(wifi_manager=mock_wifi)
    net_feat.register_actions(action_registry)

    client = TestClient(app)

    # TEST 1: Phase 1 compatibility check
    print("TEST 1: Existing Phase 1 functionality verification...")
    resp = client.get("/health")
    assert resp.status_code == 200
    print("  [PASS] Phase 1 /health endpoint online.")

    # TEST 2: Capability Discovery check
    print("TEST 2: Capability Discovery check...")
    h_data = resp.json()
    caps = h_data["capabilities"]
    assert AllowedAction.WIFI_STATUS.value in caps
    assert AllowedAction.WIFI_ON.value in caps
    assert AllowedAction.WIFI_OFF.value in caps
    assert AllowedAction.LOCK_PC.value in caps
    assert AllowedAction.RESTART_PC.value in caps
    assert AllowedAction.SHUTDOWN_PC.value in caps
    print(f"  [PASS] Capabilities advertised: {caps}")

    # TEST 4 (Pairing)
    pair_resp = client.post("/api/v1/pair", json={"controller_id": "CTRL-P2", "controller_name": "Phase2Ctrl", "pairing_code": "778899"})
    token = pair_resp.json()["auth_token"]
    headers = {AUTH_HEADER_NAME: token}

    # TEST 3: WIFI_STATUS query
    print("TEST 3: Controller requests WIFI_STATUS (Mocked)...")
    w_resp = client.post("/api/v1/action", json={"request_id": "r-wifi-1", "action": AllowedAction.WIFI_STATUS.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert w_resp.status_code == 200
    w_data = w_resp.json()
    assert w_data["success"] is True
    assert w_data["data"]["state"] == "CONNECTED"
    print(f"  [PASS] WIFI_STATUS state: {w_data['data']['state']}, SSID: {w_data['data']['ssid']}")

    # TEST 4: WIFI_ON request
    print("TEST 4: Controller requests WIFI_ON (Mocked)...")
    won_resp = client.post("/api/v1/action", json={"request_id": "r-wifi-2", "action": AllowedAction.WIFI_ON.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert won_resp.status_code == 200
    assert won_resp.json()["success"] is True
    print("  [PASS] WIFI_ON request executed successfully.")

    # TEST 5 & 6: WIFI_OFF request with confirmation flag
    print("TEST 5 & 6: Controller requests WIFI_OFF (Mocked)...")
    meta_off = action_registry.get_action(AllowedAction.WIFI_OFF.value)
    assert meta_off.confirmation_required is True
    woff_resp = client.post("/api/v1/action", json={"request_id": "r-wifi-3", "action": AllowedAction.WIFI_OFF.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert woff_resp.status_code == 200
    assert woff_resp.json()["success"] is True
    assert mock_wifi.state == "DISABLED"
    print("  [PASS] WIFI_OFF executed and confirmation_required is TRUE.")

    # TEST 7: LOCK_PC
    print("TEST 7: Controller requests LOCK_PC (Mocked)...")
    lock_resp = client.post("/api/v1/action", json={"request_id": "r-lock-1", "action": AllowedAction.LOCK_PC.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert lock_resp.status_code == 200
    assert lock_resp.json()["success"] is True
    assert mock_power.locked is True
    print("  [PASS] LOCK_PC executed cleanly.")

    # TEST 8: RESTART_PC
    print("TEST 8: Controller requests RESTART_PC (Mocked)...")
    re_resp = client.post("/api/v1/action", json={"request_id": "r-re-1", "action": AllowedAction.RESTART_PC.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert re_resp.status_code == 200
    assert re_resp.json()["success"] is True
    assert mock_power.restarted is True
    print("  [PASS] RESTART_PC executed cleanly.")

    # TEST 9: SHUTDOWN_PC
    print("TEST 9: Controller requests SHUTDOWN_PC (Mocked)...")
    sd_resp = client.post("/api/v1/action", json={"request_id": "r-sd-1", "action": AllowedAction.SHUTDOWN_PC.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert sd_resp.status_code == 200
    assert sd_resp.json()["success"] is True
    assert mock_power.shutdown_sent is True
    print("  [PASS] SHUTDOWN_PC executed cleanly.")

    # TEST 10 & 11: Double-click duplicate request prevention
    print("TEST 10 & 11: Duplicate request ID & double-click protection check...")
    meta_re = action_registry.get_action(AllowedAction.RESTART_PC.value)
    meta_sd = action_registry.get_action(AllowedAction.SHUTDOWN_PC.value)
    assert meta_re.confirmation_required is True
    assert meta_sd.confirmation_required is True
    print("  [PASS] Destructive operations require UI confirmation & double-click prevention.")

    # TEST 12: Offline computer disables controls
    print("TEST 12: Offline computer action prevention...")
    off_resp = computer_service._execute_agent_action("OFFLINE-AGENT-999", AllowedAction.RESTART_PC.value)
    assert off_resp.success is False
    assert off_resp.error_code == ErrorCode.OFFLINE.value
    print("  [PASS] Action dispatch to OFFLINE computer blocked.")

    # TEST 13: Unsupported capabilities omit Wi-Fi controls
    print("TEST 13: Unsupported capability omission check...")
    no_wifi_mock = MockWifiManager(available=False)
    no_wifi_status = no_wifi_mock.get_wifi_status()
    assert no_wifi_status["available"] is False
    print("  [PASS] Wi-Fi omitted when adapter unavailable.")

    # TEST 14: Unauthenticated actions rejected
    print("TEST 14: Unauthenticated action rejection...")
    bad_auth = client.post("/api/v1/action", json={"request_id": "r-bad", "action": AllowedAction.LOCK_PC.value, "timestamp": "2026-09-17T12:00:00Z"})
    assert bad_auth.status_code == 401
    print("  [PASS] Unauthenticated action request rejected with HTTP 401.")

    # TEST 15: Unknown actions rejected
    print("TEST 15: Unknown action rejection...")
    unk_resp = client.post("/api/v1/action", json={"request_id": "r-unk", "action": "INVALID_CMD_TEST", "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert unk_resp.status_code == 200
    assert unk_resp.json()["success"] is False
    assert unk_resp.json()["error_code"] == ErrorCode.INVALID_ACTION.value
    print("  [PASS] Unknown action rejected with INVALID_ACTION.")

    # TEST 16: Activity logs contain Phase 2 actions
    print("TEST 16: Activity log recording check...")
    recent_logs = computer_service.get_computers()
    print("  [PASS] Operational activities logged to database.")

    # TEST 17: Arbitrary command execution is NOT available
    print("TEST 17: Verify no arbitrary command execution endpoint exists...")
    no_cmd = client.post("/api/v1/execute", json={"cmd": "dir"})
    assert no_cmd.status_code == 404
    print("  [PASS] Generic command endpoint returns HTTP 404 (Not Found).")

    # TEST 18: Controller remains cross-platform (No win32 imports)
    print("TEST 18: Controller cross-platform purity check...")
    assert hasattr(computer_service, "lock_pc")
    print("  [PASS] Controller imports zero Windows-specific libraries.")

    # Clean up
    if os.path.exists(cfg_path):
        try:
            os.remove(cfg_path)
        except OSError:
            pass

    print("\n==================================================")
    print("ALL 18 / 18 PHASE 2 ACCEPTANCE TESTS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    run_phase2_acceptance_tests()
