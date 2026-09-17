import sqlite3
from controller.utils.logging_config import logger


def run_migrations(conn: sqlite3.Connection):
    cursor = conn.cursor()

    # Table: computers
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS computers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            port INTEGER NOT NULL,
            auth_token TEXT,
            os_name TEXT DEFAULT 'Windows',
            agent_version TEXT DEFAULT '1.0.0',
            status TEXT DEFAULT 'OFFLINE',
            last_seen TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_computers_agent_id ON computers(agent_id)"
    )

    # Table: computer_capabilities
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS computer_capabilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            capability_name TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(agent_id, capability_name)
        )
    """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_capabilities_agent_id ON computer_capabilities(agent_id)"
    )

    # Table: allowed_applications
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS allowed_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_id TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            executable_name TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """
    )

    # Table: file_roots (Approved Logical Roots Table)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS file_roots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root_id TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """
    )

    # Table: activity
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT,
            computer_id TEXT,
            computer_name TEXT,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            created_at TEXT NOT NULL
        )
    """
    )

    # Table: settings
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT
        )
    """
    )

    conn.commit()
    logger.info("SQLite database schema migrations executed successfully.")
