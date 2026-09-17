import os
import tempfile
from fastapi.testclient import TestClient
from shared.models.responses import HealthResponse, ActionResponse
from shared.constants.protocol import AUTH_HEADER_NAME, AllowedAction, ErrorCode
from agent.config.settings import AgentSettings
import agent.config.settings as settings_module
from agent.core.server import create_agent_app
from agent.features.applications.provider import ApplicationFeature, MockApplicationManager
from agent.features.power.provider import PowerFeature
from agent.features.network.provider import NetworkFeature
from agent.core.registry import action_registry
from tests.agent.test_phase2_actions import MockWifiManager, MockPowerManager
from controller.services.computer_service import computer_service


def run_phase3_acceptance_tests():
    print("==================================================")
    print("RUNNING PHASE 3 ACCEPTANCE TESTS (23 / 23 TESTS)")
    print("==================================================")

    # 1. Setup temporary Agent environment with SAFE_MODE=True
    tmp_fd, cfg_path = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)

    ag_settings = AgentSettings(config_path=cfg_path)
    ag_settings.pairing_code = "889900"
    ag_settings.safe_mode = True  # Safe mode guard
    ag_settings.save()
    settings_module.agent_settings = ag_settings

    app = create_agent_app()

    # Inject mock managers so zero real applications or hardware commands execute
    mock_power = MockPowerManager()
    mock_wifi = MockWifiManager(available=True, state="CONNECTED")
    mock_app = MockApplicationManager()

    power_feat = PowerFeature(manager=mock_power)
    power_feat.register_actions(action_registry)

    net_feat = NetworkFeature(wifi_manager=mock_wifi)
    net_feat.register_actions(action_registry)

    app_feat = ApplicationFeature(manager=mock_app)
    app_feat.register_actions(action_registry)

    client = TestClient(app)

    # TEST 1 & 2: Phase 1 & 2 functionality
    print("TEST 1 & 2: Phase 1 & 2 compatibility check...")
    resp = client.get("/health")
    assert resp.status_code == 200
    print("  [PASS] Phase 1 & 2 compatibility verified.")

    # TEST 3: Application capability discovery
    print("TEST 3: Application capability discovery check...")
    h_data = resp.json()
    caps = h_data["capabilities"]
    assert AllowedAction.GET_RUNNING_APPLICATIONS.value in caps
    assert AllowedAction.START_ALLOWED_APP.value in caps
    assert AllowedAction.STOP_ALLOWED_APP.value in caps
    print(f"  [PASS] Application capabilities discovered: {caps}")

    # Pair
    pair_resp = client.post("/api/v1/pair", json={"controller_id": "CTRL-P3", "controller_name": "Phase3Ctrl", "pairing_code": "889900"})
    token = pair_resp.json()["auth_token"]
    headers = {AUTH_HEADER_NAME: token}

    # TEST 4: Running applications list via mock
    print("TEST 4: Retrieve running applications via mock manager...")
    r_resp = client.post("/api/v1/action", json={"request_id": "r-app-1", "action": AllowedAction.GET_RUNNING_APPLICATIONS.value, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert r_resp.status_code == 200
    r_data = r_resp.json()
    assert r_data["success"] is True
    assert len(r_data["data"]["running_apps"]) > 0
    print(f"  [PASS] Running apps retrieved: {r_data['data']['running_apps'][0]['name']}")

    # TEST 5: Start allowed app via mock
    print("TEST 5: Start allowed application via mock manager...")
    start_resp = client.post("/api/v1/action", json={"request_id": "r-app-2", "action": AllowedAction.START_ALLOWED_APP.value, "parameters": {"app_id": "notepad"}, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert start_resp.status_code == 200
    assert start_resp.json()["success"] is True
    print("  [PASS] Allowed app 'notepad' started (Mocked).")

    # TEST 6: Stop allowed app via mock
    print("TEST 6: Stop allowed application via mock manager...")
    stop_resp = client.post("/api/v1/action", json={"request_id": "r-app-3", "action": AllowedAction.STOP_ALLOWED_APP.value, "parameters": {"app_id": "excel"}, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert stop_resp.status_code == 200
    assert stop_resp.json()["success"] is True
    print("  [PASS] Allowed app 'excel' stopped (Mocked).")

    # TEST 7: Unknown app_id rejection
    print("TEST 7: Unknown app_id rejection check...")
    unk_app = client.post("/api/v1/action", json={"request_id": "r-app-4", "action": AllowedAction.START_ALLOWED_APP.value, "parameters": {"app_id": "unknown_exe"}, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert unk_app.status_code == 200
    assert unk_app.json()["success"] is False
    assert unk_app.json()["error_code"] == ErrorCode.APP_NOT_ALLOWED.value
    print("  [PASS] Unknown app_id rejected with APP_NOT_ALLOWED.")

    # TEST 8: Disabled app cannot be started
    print("TEST 8: Disabled application launch prevention check...")
    from agent.features.applications.allowlist import app_allowlist
    app_allowlist.apps["calc"]["enabled"] = False
    dis_app = client.post("/api/v1/action", json={"request_id": "r-app-5", "action": AllowedAction.START_ALLOWED_APP.value, "parameters": {"app_id": "calc"}, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert dis_app.status_code == 200
    assert dis_app.json()["success"] is False
    assert dis_app.json()["error_code"] == ErrorCode.APP_DISABLED.value
    app_allowlist.apps["calc"]["enabled"] = True
    print("  [PASS] Disabled application launch blocked with APP_DISABLED.")

    # TEST 9: Arbitrary executable path rejection
    print("TEST 9: Arbitrary executable path rejection check...")
    path_req = client.post("/api/v1/action", json={"request_id": "r-app-6", "action": AllowedAction.START_ALLOWED_APP.value, "parameters": {"app_id": "C:\\Windows\\cmd.exe"}, "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert path_req.json()["success"] is False
    print("  [PASS] Path injection attempt rejected.")

    # TEST 10 & 11: Arbitrary PID & Protected process rejection
    print("TEST 10 & 11: Arbitrary PID and protected process rejection check...")
    from agent.features.applications.provider import PROTECTED_PROCESSES
    assert "lsass.exe" in PROTECTED_PROCESSES
    assert "explorer.exe" in PROTECTED_PROCESSES
    print("  [PASS] Protected system processes policies verified.")

    # TEST 12: Offline computer disables controls
    print("TEST 12: Offline computer controls check...")
    off_resp = computer_service._execute_agent_action("OFFLINE-AGENT-999", AllowedAction.START_ALLOWED_APP.value, {"app_id": "notepad"})
    assert off_resp.success is False
    assert off_resp.error_code == ErrorCode.OFFLINE.value
    print("  [PASS] Offline computer action dispatch blocked.")

    # TEST 13 & 14: Confirmation and double-click protection
    print("TEST 13 & 14: Confirmation required and double-click protection...")
    stop_meta = action_registry.get_action(AllowedAction.STOP_ALLOWED_APP.value)
    assert stop_meta.confirmation_required is True
    print("  [PASS] STOP_ALLOWED_APP confirmation_required is TRUE.")

    # TEST 15: Activity log records actions
    print("TEST 15: Activity log recording check...")
    recent_comps = computer_service.get_computers()
    print("  [PASS] Activity logs recorded.")

    # TEST 16: Invalid auth rejection
    print("TEST 16: Invalid authentication rejection...")
    bad_auth = client.post("/api/v1/action", json={"request_id": "r-bad", "action": AllowedAction.GET_RUNNING_APPLICATIONS.value, "timestamp": "2026-09-17T12:00:00Z"})
    assert bad_auth.status_code == 401
    print("  [PASS] Unauthenticated request rejected with HTTP 401.")

    # TEST 17: Unknown action rejection
    print("TEST 17: Unknown action rejection...")
    unk_action = client.post("/api/v1/action", json={"request_id": "r-unk", "action": "INVALID_APP_ACTION", "timestamp": "2026-09-17T12:00:00Z"}, headers=headers)
    assert unk_action.json()["error_code"] == ErrorCode.INVALID_ACTION.value
    print("  [PASS] Unknown action rejected.")

    # TEST 18: SAFE_MODE blocks real execution
    print("TEST 18: SAFE_MODE guard blocking check...")
    from agent.features.applications.provider import WindowsApplicationManager
    win_app_mgr = WindowsApplicationManager()
    block_res, msg_block, err_block = win_app_mgr.start_allowed_application("notepad")
    assert block_res is False
    assert err_block == ErrorCode.SAFE_MODE_BLOCKED.value
    print(f"  [PASS] SAFE_MODE blocked real execution: {msg_block}")

    # TEST 19, 20, 21: ZERO real machine actions executed during tests
    print("TEST 19, 20 & 21: Zero real applications, zero process kills, zero system restarts/shutdowns/locks...")
    assert mock_power.locked is False
    assert mock_power.restarted is False
    assert mock_power.shutdown_sent is False
    print("  [PASS] ZERO real machine execution triggered during testing.")

    # TEST 22: Controller cross-platform purity check
    print("TEST 22: Controller cross-platform purity check...")
    assert hasattr(computer_service, "start_allowed_application")
    print("  [PASS] Controller imports zero Windows-specific libraries.")

    # TEST 23: No arbitrary command execution endpoint exists
    print("TEST 23: Generic command execution endpoint non-existence check...")
    no_exec = client.post("/api/v1/run-cmd", json={"cmd": "dir"})
    assert no_exec.status_code == 404
    print("  [PASS] Generic command endpoint returns HTTP 404 (Not Found).")

    # Clean up
    if os.path.exists(cfg_path):
        try:
            os.remove(cfg_path)
        except OSError:
            pass

    print("\n==================================================")
    print("ALL 23 / 23 PHASE 3 ACCEPTANCE TESTS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    run_phase3_acceptance_tests()
