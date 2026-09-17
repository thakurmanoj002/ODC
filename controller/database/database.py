import sqlite3
import os
from datetime import datetime, timezone
from typing import List, Optional
from controller.database.models import ComputerRecord, ActivityRecord
from controller.database.migrations import run_migrations
from controller.utils.logging_config import logger

DB_FILE = "lan_control.db"


class Database:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            run_migrations(conn)

    # --- Computer Operations ---
    def add_computer(self, comp: ComputerRecord) -> ComputerRecord:
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO computers (agent_id, display_name, ip_address, port, auth_token, os_name, agent_version, status, last_seen, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    comp.agent_id,
                    comp.display_name,
                    comp.ip_address,
                    comp.port,
                    comp.auth_token,
                    comp.os_name,
                    comp.agent_version,
                    comp.status,
                    comp.last_seen or now,
                    now,
                    now,
                ),
            )
            comp.id = cursor.lastrowid
            conn.commit()
            logger.info(f"Added new computer to database: {comp.display_name} ({comp.agent_id})")
            return comp

    def get_all_computers(self) -> List[ComputerRecord]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM computers ORDER BY display_name ASC")
            rows = cursor.fetchall()
            return [
                ComputerRecord(
                    id=row["id"],
                    agent_id=row["agent_id"],
                    display_name=row["display_name"],
                    ip_address=row["ip_address"],
                    port=row["port"],
                    auth_token=row["auth_token"],
                    os_name=row["os_name"] or "Windows",
                    agent_version=row["agent_version"] or "1.0.0",
                    status=row["status"] or "OFFLINE",
                    last_seen=row["last_seen"] or "",
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    def get_computer_by_agent_id(self, agent_id: str) -> Optional[ComputerRecord]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM computers WHERE agent_id = ?", (agent_id,))
            row = cursor.fetchone()
            if row:
                return ComputerRecord(
                    id=row["id"],
                    agent_id=row["agent_id"],
                    display_name=row["display_name"],
                    ip_address=row["ip_address"],
                    port=row["port"],
                    auth_token=row["auth_token"],
                    os_name=row["os_name"] or "Windows",
                    agent_version=row["agent_version"] or "1.0.0",
                    status=row["status"] or "OFFLINE",
                    last_seen=row["last_seen"] or "",
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            return None

    def update_computer_status(self, agent_id: str, status: str, last_seen: str = None):
        now = datetime.now(timezone.utc).isoformat()
        ls = last_seen or now
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE computers SET status = ?, last_seen = ?, updated_at = ? WHERE agent_id = ?",
                (status, ls, now, agent_id),
            )
            conn.commit()

    def update_computer_details(
        self, agent_id: str, display_name: str, ip_address: str, port: int, auth_token: str = None
    ):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if auth_token:
                cursor.execute(
                    """
                    UPDATE computers
                    SET display_name = ?, ip_address = ?, port = ?, auth_token = ?, updated_at = ?
                    WHERE agent_id = ?
                """,
                    (display_name, ip_address, port, auth_token, now, agent_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE computers
                    SET display_name = ?, ip_address = ?, port = ?, updated_at = ?
                    WHERE agent_id = ?
                """,
                    (display_name, ip_address, port, now, agent_id),
                )
            conn.commit()

    def delete_computer(self, agent_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM computers WHERE agent_id = ?", (agent_id,))
            cursor.execute("DELETE FROM computer_capabilities WHERE agent_id = ?", (agent_id,))
            conn.commit()
            logger.info(f"Removed computer {agent_id} from database")

    # --- Capability Persistence Operations ---
    def save_computer_capabilities(self, agent_id: str, capabilities: List[str]):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for cap in capabilities:
                cursor.execute(
                    """
                    INSERT INTO computer_capabilities (agent_id, capability_name, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(agent_id, capability_name) DO UPDATE SET updated_at = ?
                """,
                    (agent_id, cap, now, now),
                )
            conn.commit()

    def get_computer_capabilities(self, agent_id: str) -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT capability_name FROM computer_capabilities WHERE agent_id = ?", (agent_id,))
            rows = cursor.fetchall()
            return [row["capability_name"] for row in rows]

    # --- Activity Log Operations ---
    def log_activity(
        self,
        action: str,
        status: str,
        message: str,
        computer_id: str = None,
        computer_name: str = None,
        request_id: str = "",
    ):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO activity (request_id, computer_id, computer_name, action, status, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (request_id, computer_id, computer_name, action, status, message, now),
            )
            conn.commit()

    def get_recent_activities(self, limit: int = 100) -> List[ActivityRecord]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()
            return [
                ActivityRecord(
                    id=row["id"],
                    request_id=row["request_id"] or "",
                    computer_id=row["computer_id"],
                    computer_name=row["computer_name"],
                    action=row["action"],
                    status=row["status"],
                    message=row["message"] or "",
                    created_at=row["created_at"],
                )
                for row in rows
            ]


db = Database()
