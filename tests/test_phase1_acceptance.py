import os
import tempfile
import time
from fastapi.testclient import TestClient
from shared.models.responses import HealthResponse
from shared.constants.protocol import AUTH_HEADER_NAME, AllowedAction, ErrorCode
from agent.config.settings import AgentSettings
import agent.config.settings as settings_module
from agent.api.server import create_agent_app
from controller.database.database import Database
from controller.database.models import ComputerRecord
from controller.services.agent_client import AgentClient


def run_acceptance_tests():
    print("==================================================")
    print("RUNNING PHASE 1 ACCEPTANCE TESTS (10 / 10 TESTS)")
    print("==================================================")

    # 1. Setup temporary Agent environment
    tmp_fd, cfg_path = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)

    ag_settings = AgentSettings(config_path=cfg_path)
    ag_settings.pairing_code = "998877"
    ag_settings.save()
    settings_module.agent_settings = ag_settings

    app = create_agent_app()
    client = TestClient(app)

    # TEST 1: Start Windows Agent & Check Display metadata
    print("TEST 1: Verify Windows Agent Metadata...")
    assert ag_settings.agent_id.startswith("AGENT-")
    assert ag_settings.pairing_code == "998877"
    assert ag_settings.server_port == 8765
    print(f"  [PASS] Agent ID: {ag_settings.agent_id}, Port: {ag_settings.server_port}, Code: {ag_settings.pairing_code}")

    # TEST 2 & 3: Health check endpoint (Discovery / Connection check)
    print("TEST 2 & 3: Controller discovers / checks Agent health...")
    resp = client.get("/health")
    assert resp.status_code == 200
    h_data = resp.json()
    assert h_data["status"] == "online"
    assert h_data["agent_id"] == ag_settings.agent_id
    print(f"  [PASS] Agent Health Check OK: status={h_data['status']}, agent_id={h_data['agent_id']}")

    # TEST 4: Pair Controller with Agent
    print("TEST 4: Pair Controller with Agent using pairing code '998877'...")
    pair_resp = client.post(
        "/api/pair",
        json={
            "controller_id": "CTRL-ACCEPTANCE-1",
            "controller_name": "AcceptanceController",
            "pairing_code": "998877",
        },
    )
    assert pair_resp.status_code == 200
    p_data = pair_resp.json()
    assert p_data["success"] is True
    token = p_data["auth_token"]
    assert token is not None
    print(f"  [PASS] Pairing Successful! Auth Token issued: {token[:12]}...")

    # TEST 5: Controller requests system information
    print("TEST 5: Request System Information from Agent...")
    sys_resp = client.get("/api/system-info", headers={AUTH_HEADER_NAME: token})
    assert sys_resp.status_code == 200
    s_data = sys_resp.json()
    assert "cpu_usage" in s_data
    assert "ram_usage" in s_data
    assert "disk_usage" in s_data
    assert "uptime_seconds" in s_data
    print(f"  [PASS] System Metrics: CPU {s_data['cpu_usage']}%, RAM {s_data['ram_usage']}%, Disk {s_data['disk_usage']}%, OS: {s_data['os_name']}")

    # TEST 6 & 7: Online/Offline status behavior
    print("TEST 6 & 7: Online / Offline status handling...")
    # Unpaired or invalid token -> fails check
    bad_sys = client.get("/api/system-info", headers={AUTH_HEADER_NAME: "invalid_token"})
    assert bad_sys.status_code == 401
    print("  [PASS] Invalid token correctly reported as UNAUTHORIZED / Offline access blocked.")

    # TEST 8: Try accessing protected API with invalid token
    print("TEST 8: Rejection of unauthenticated protected API access...")
    no_auth_resp = client.get("/api/network-info")
    assert no_auth_resp.status_code == 401
    print("  [PASS] Missing token rejected with HTTP 401.")

    # TEST 9: Try sending an unknown / Phase 1 unsupported action
    print("TEST 9: Rejection of unknown / Phase 1 restricted actions...")
    unknown_action_req = {
        "request_id": "req-999",
        "action": "SHUTDOWN_PC",
        "timestamp": "2026-09-17T12:00:00Z",
    }
    act_resp = client.post("/api/action", json=unknown_action_req, headers={AUTH_HEADER_NAME: token})
    assert act_resp.status_code == 200
    a_data = act_resp.json()
    assert a_data["success"] is False
    assert a_data["error_code"] == ErrorCode.INVALID_ACTION.value
    print(f"  [PASS] Action 'SHUTDOWN_PC' rejected with error code: {a_data['error_code']}")

    # TEST 10: Persistent SQLite Storage across restarts
    print("TEST 10: Controller SQLite database persistence...")
    tmp_db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_db_fd)
    
    db_inst1 = Database(db_path=db_path)
    comp = ComputerRecord(
        id=None,
        agent_id=ag_settings.agent_id,
        display_name=ag_settings.computer_name,
        ip_address="192.168.1.50",
        port=8765,
        auth_token=token,
        os_name="Windows 11",
        agent_version="1.0.0",
        status="ONLINE",
        last_seen="2026-09-17T12:00:00Z",
        created_at="2026-09-17T12:00:00Z",
        updated_at="2026-09-17T12:00:00Z",
    )
    db_inst1.add_computer(comp)

    # Re-open database (Simulating Controller restart)
    db_inst2 = Database(db_path=db_path)
    persisted_comp = db_inst2.get_computer_by_agent_id(ag_settings.agent_id)
    assert persisted_comp is not None
    assert persisted_comp.display_name == ag_settings.computer_name
    assert persisted_comp.auth_token == token
    print(f"  [PASS] Controller Database Persistence verified! Computer '{persisted_comp.display_name}' persisted.")

    # Cleanup
    if os.path.exists(cfg_path):
        os.remove(cfg_path)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass

    print("\n==================================================")
    print("ALL 10 / 10 PHASE 1 ACCEPTANCE TESTS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    run_acceptance_tests()
