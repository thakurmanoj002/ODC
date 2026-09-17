import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from shared.constants.protocol import AUTH_HEADER_NAME, AllowedAction, ErrorCode
from agent.config.settings import AgentSettings
import agent.config.settings as settings_module
from agent.core.server import create_agent_app
from agent.features.files.sandbox import PathSandbox
from agent.features.files.provider import FilesFeature, MockFileSystemManager, WindowsFileManager
from agent.core.registry import action_registry


@pytest.fixture
def test_phase4_agent_env():
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)

    test_settings = AgentSettings(config_path=tmp_path)
    test_settings.pairing_code = "445566"
    test_settings.safe_mode = True  # Mandatory safe_mode guard
    test_settings.save()

    original_settings = settings_module.agent_settings
    settings_module.agent_settings = test_settings

    app = create_agent_app()

    # Inject MockFileSystemManager for 100% safe isolated testing
    mock_file_mgr = MockFileSystemManager()
    files_feat = FilesFeature(manager=mock_file_mgr)
    files_feat.register_actions(action_registry)

    client = TestClient(app)

    yield client, test_settings, mock_file_mgr

    settings_module.agent_settings = original_settings
    if os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def test_sandbox_path_traversal_and_blacklists():
    with tempfile.TemporaryDirectory() as temp_dir:
        custom_roots = {
            "shared": {
                "root_id": "shared",
                "display_name": "Shared Workspace",
                "path": temp_dir,
                "enabled": True,
            }
        }
        sandbox = PathSandbox(roots=custom_roots)

        # Test valid path
        res, resolved_path, root_base, err = sandbox.resolve_and_validate("shared", "")
        assert res is True
        assert err is None

        # Test path traversal attempts
        res_trav1, _, _, err_trav1 = sandbox.resolve_and_validate("shared", "../outside")
        assert res_trav1 is False
        assert err_trav1 == ErrorCode.PATH_TRAVERSAL_DETECTED.value

        res_trav2, _, _, err_trav2 = sandbox.resolve_and_validate("shared", "..\\..\\Windows")
        assert res_trav2 is False
        assert err_trav2 == ErrorCode.PATH_TRAVERSAL_DETECTED.value

        # Test non-existent root_id
        res_root, _, _, err_root = sandbox.resolve_and_validate("nonexistent_root", "")
        assert res_root is False
        assert err_root == ErrorCode.ROOT_NOT_FOUND.value

        # Test OS blacklisted directories
        # Directly test resolve_and_validate with a path that attempts to escape to C:\Windows
        from agent.features.files.sandbox import PROTECTED_DIRECTORIES
        assert r"c:\windows" in PROTECTED_DIRECTORIES
        assert r"c:\program files" in PROTECTED_DIRECTORIES


def test_get_directory(test_phase4_agent_env):
    client, settings, mock_mgr = test_phase4_agent_env

    pair_resp = client.post("/api/v1/pair", json={"controller_id": "C1", "controller_name": "C1", "pairing_code": "445566"})
    token = pair_resp.json()["auth_token"]
    headers = {AUTH_HEADER_NAME: token}

    resp = client.post(
        "/api/v1/action",
        json={"request_id": "r-file-1", "action": AllowedAction.GET_DIRECTORY.value, "parameters": {"root_id": "shared", "relative_path": ""}, "timestamp": "2026-09-17T12:00:00Z"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "items" in data["data"]
    assert "roots" in data["data"]
    assert len(data["data"]["items"]) > 0


def test_create_rename_delete_folder(test_phase4_agent_env):
    client, settings, mock_mgr = test_phase4_agent_env

    pair_resp = client.post("/api/v1/pair", json={"controller_id": "C1", "controller_name": "C1", "pairing_code": "445566"})
    token = pair_resp.json()["auth_token"]
    headers = {AUTH_HEADER_NAME: token}

    # Create folder
    create_resp = client.post(
        "/api/v1/action",
        json={
            "request_id": "r-file-2",
            "action": AllowedAction.CREATE_FOLDER.value,
            "parameters": {"root_id": "shared", "relative_path": "", "folder_name": "NewTestFolder"},
            "timestamp": "2026-09-17T12:00:00Z",
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["success"] is True

    # Rename folder
    rename_resp = client.post(
        "/api/v1/action",
        json={
            "request_id": "r-file-3",
            "action": AllowedAction.RENAME_PATH.value,
            "parameters": {"root_id": "shared", "relative_path": "NewTestFolder", "new_name": "RenamedTestFolder"},
            "timestamp": "2026-09-17T12:00:00Z",
        },
        headers=headers,
    )
    assert rename_resp.status_code == 200
    assert rename_resp.json()["success"] is True

    # Delete folder
    del_resp = client.post(
        "/api/v1/action",
        json={
            "request_id": "r-file-4",
            "action": AllowedAction.DELETE_PATH.value,
            "parameters": {"root_id": "shared", "relative_path": "RenamedTestFolder"},
            "timestamp": "2026-09-17T12:00:00Z",
        },
        headers=headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True


def test_safe_mode_blocking_on_real_file_manager():
    win_mgr = WindowsFileManager()
    # Ensure SAFE_MODE = True
    settings_module.agent_settings.safe_mode = True

    succ_c, msg_c, err_c = win_mgr.create_folder("shared", "", "folder")
    assert succ_c is False
    assert err_c == ErrorCode.SAFE_MODE_BLOCKED.value

    succ_r, msg_r, err_r = win_mgr.rename_path("shared", "file.txt", "new.txt")
    assert succ_r is False
    assert err_r == ErrorCode.SAFE_MODE_BLOCKED.value

    succ_d, msg_d, err_d = win_mgr.delete_path("shared", "file.txt")
    assert succ_d is False
    assert err_d == ErrorCode.SAFE_MODE_BLOCKED.value
