"""
Database migration: Add payload_hash column to erp_raw_data table.

Run this once to update existing database.
"""

import hashlib
import json
import sqlite3
from pathlib import Path

DB_PATH = Path("data/job_sync.db")


def calculate_hash(payload_json: str) -> str:
    """Calculate MD5 hash of JSON payload."""
    payload = json.loads(payload_json)
    sorted_json = json.dumps(payload, sort_keys=True)
    return hashlib.md5(sorted_json.encode()).hexdigest()


def migrate():
    """Add payload_hash column and populate for existing records."""
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(erp_raw_data)")
    columns = [row[1] for row in cursor.fetchall()]

    if "payload_hash" in columns:
        print("✅ payload_hash column already exists")
        conn.close()
        return

    print("Adding payload_hash column...")
    cursor.execute(
        "ALTER TABLE erp_raw_data ADD COLUMN payload_hash TEXT"
    )

    print("Calculating hashes for existing records...")
    cursor.execute("SELECT id, payload_json FROM erp_raw_data")
    rows = cursor.fetchall()

    for record_id, payload_json in rows:
        payload_hash = calculate_hash(payload_json)
        cursor.execute(
            "UPDATE erp_raw_data SET payload_hash = ? WHERE id = ?",
            (payload_hash, record_id),
        )

    print("Creating index on payload_hash...")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_payload_hash "
        "ON erp_raw_data(payload_hash)"
    )

    conn.commit()
    conn.close()

    print(f"✅ Migration complete! Updated {len(rows)} records")


if __name__ == "__main__":
    migrate()
