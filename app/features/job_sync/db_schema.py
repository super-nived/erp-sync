"""
Job Sync Database Schema

SQLite tables for ERP sync state management.
Following task.md architecture: erp_raw_data, job_queue, push_log.
"""

import sqlite3
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

DB_PATH = Path("data/job_sync.db")


def get_connection() -> sqlite3.Connection:
    """
    Get SQLite database connection.

    Returns:
        Database connection
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    """Initialize database tables if they don't exist."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        create_erp_raw_data_table(cursor)
        create_job_queue_table(cursor)
        create_push_log_table(cursor)

        conn.commit()
        conn.close()
        logger.info("✅ Job sync database initialized")

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise


def create_erp_raw_data_table(cursor: sqlite3.Cursor) -> None:
    """Create erp_raw_data table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS erp_raw_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            erp_id TEXT UNIQUE NOT NULL,
            payload_json TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_erp_id
        ON erp_raw_data(erp_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_payload_hash
        ON erp_raw_data(payload_hash)
    """)


def create_job_queue_table(cursor: sqlite3.Cursor) -> None:
    """Create job_queue table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload_ref INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            retry_count INTEGER DEFAULT 0,
            last_error TEXT,
            last_attempt_at TEXT,
            next_attempt_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (payload_ref) REFERENCES erp_raw_data(id)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_job_status
        ON job_queue(status, next_attempt_at)
    """)


def create_push_log_table(cursor: sqlite3.Cursor) -> None:
    """Create push_log table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS push_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            response_code INTEGER,
            response_body TEXT,
            sent_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES job_queue(id)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_job_id
        ON push_log(job_id)
    """)
