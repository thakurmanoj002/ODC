import os
import tempfile
import pytest
from controller.database.database import Database
from controller.database.models import ComputerRecord


@pytest.fixture
def temp_db():
    tmp_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)

    test_database = Database(db_path=db_path)
    yield test_database

    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


def test_add_get_delete_computer(temp_db):
    comp = ComputerRecord(
        id=None,
        agent_id="AGENT-TEST1",
        display_name="Test-PC-01",
        ip_address="192.168.1.100",
        port=8765,
        auth_token="tok_123456",
        os_name="Windows 11",
        agent_version="1.0.0",
        status="ONLINE",
        last_seen="2026-09-17T12:00:00Z",
        created_at="2026-09-17T12:00:00Z",
        updated_at="2026-09-17T12:00:00Z",
    )

    added = temp_db.add_computer(comp)
    assert added.id is not None

    all_comps = temp_db.get_all_computers()
    assert len(all_comps) == 1
    assert all_comps[0].agent_id == "AGENT-TEST1"

    found = temp_db.get_computer_by_agent_id("AGENT-TEST1")
    assert found is not None
    assert found.display_name == "Test-PC-01"

    temp_db.update_computer_status("AGENT-TEST1", "OFFLINE")
    found_updated = temp_db.get_computer_by_agent_id("AGENT-TEST1")
    assert found_updated.status == "OFFLINE"

    temp_db.delete_computer("AGENT-TEST1")
    assert temp_db.get_computer_by_agent_id("AGENT-TEST1") is None


def test_activity_logging(temp_db):
    temp_db.log_activity(
        action="TEST_ACTION",
        status="SUCCESS",
        message="Executed test action cleanly",
        computer_id="AGENT-TEST1",
        computer_name="Test-PC-01",
    )

    activities = temp_db.get_recent_activities(limit=10)
    assert len(activities) == 1
    assert activities[0].action == "TEST_ACTION"
    assert activities[0].status == "SUCCESS"
