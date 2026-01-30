"""
Job Sync Database Helpers

Helper functions for job queue database operations.
Each function under 30 lines with single responsibility.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.logging import get_logger
from app.features.job_sync.db_schema import get_connection

logger = get_logger(__name__)


def now_utc() -> str:
    """Get current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def calculate_payload_hash(payload: dict) -> str:
    """
    Calculate hash of payload for change detection.

    Args:
        payload: Data dictionary

    Returns:
        MD5 hash string
    """
    payload_json = json.dumps(payload, sort_keys=True)
    return hashlib.md5(payload_json.encode()).hexdigest()


def insert_raw_erp_data(erp_id: str, payload: dict) -> tuple[int, bool] | tuple[None, bool]:
    """
    Insert or update raw ERP data using hash comparison.

    Args:
        erp_id: Unique ERP identifier
        payload: Raw ERP data

    Returns:
        Tuple of (record_id, is_updated)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        new_hash = calculate_payload_hash(payload)
        new_payload_json = json.dumps(payload)

        cursor.execute(
            "SELECT id, payload_hash FROM erp_raw_data WHERE erp_id = ?",
            (erp_id,),
        )
        existing = cursor.fetchone()

        if existing:
            record_id = existing[0]
            old_hash = existing[1]

            is_updated = old_hash != new_hash

            if is_updated:
                cursor.execute(
                    """
                    UPDATE erp_raw_data
                    SET payload_json = ?, payload_hash = ?, fetched_at = ?
                    WHERE id = ?
                    """,
                    (new_payload_json, new_hash, now_utc(), record_id),
                )
                conn.commit()
                logger.info(f"🔄 Updated record {erp_id} (hash changed)")

            conn.close()
            return record_id, is_updated
        else:
            cursor.execute(
                """
                INSERT INTO erp_raw_data
                (erp_id, payload_json, payload_hash, fetched_at)
                VALUES (?, ?, ?, ?)
                """,
                (erp_id, new_payload_json, new_hash, now_utc()),
            )
            record_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return record_id, False

    except Exception as e:
        logger.error(f"❌ Error inserting raw data: {str(e)}")
        return None, False


def create_job_for_payload(
    payload_ref: int, force_requeue: bool = False
) -> int | None:
    """
    Create a job queue entry or requeue if done.

    Args:
        payload_ref: Reference to erp_raw_data.id
        force_requeue: Reset done jobs to queued

    Returns:
        Job ID if created, None on error
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, status FROM job_queue WHERE payload_ref = ?",
            (payload_ref,),
        )
        existing = cursor.fetchone()

        if existing:
            job_id, status = existing[0], existing[1]

            if force_requeue and status == "done":
                now = now_utc()
                cursor.execute(
                    """
                    UPDATE job_queue
                    SET status = 'queued', updated_at = ?,
                        next_attempt_at = ?, retry_count = 0
                    WHERE id = ?
                    """,
                    (now, now, job_id),
                )
                conn.commit()
                logger.info(f"🔄 Requeued job {job_id} for updated data")

            conn.close()
            return job_id

        now = now_utc()
        cursor.execute(
            """
            INSERT INTO job_queue
            (payload_ref, status, created_at, updated_at, next_attempt_at)
            VALUES (?, 'queued', ?, ?, ?)
            """,
            (payload_ref, now, now, now),
        )
        job_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return job_id

    except Exception as e:
        logger.error(f"❌ Error creating job: {str(e)}")
        return None


def get_next_queued_job() -> dict[str, Any] | None:
    """
    Get next queued job and mark as processing.

    Returns:
        Job dict with payload, or None if no jobs
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT j.id, j.payload_ref, e.payload_json
            FROM job_queue j
            JOIN erp_raw_data e ON j.payload_ref = e.id
            WHERE j.status = 'queued'
            AND j.next_attempt_at <= ?
            ORDER BY j.created_at ASC
            LIMIT 1
            """,
            (now_utc(),),
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        job_id, payload_ref, payload_json = row

        cursor.execute(
            """
            UPDATE job_queue
            SET status = 'processing', last_attempt_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now_utc(), now_utc(), job_id),
        )
        conn.commit()
        conn.close()

        return {
            "id": job_id,
            "payload_ref": payload_ref,
            "payload": json.loads(payload_json),
        }

    except Exception as e:
        logger.error(f"❌ Error getting queued job: {str(e)}")
        return None


def mark_job_done(job_id: int) -> None:
    """Mark job as completed."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE job_queue
            SET status = 'done', updated_at = ?
            WHERE id = ?
            """,
            (now_utc(), job_id),
        )
        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error marking job done: {str(e)}")


def mark_job_failed(job_id: int, error_msg: str) -> None:
    """
    Mark job as failed with retry logic.

    Args:
        job_id: Job ID
        error_msg: Error message
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT retry_count FROM job_queue WHERE id = ?", (job_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return

        retry_count = row[0] + 1
        max_retries = 5
        backoff_minutes = min(retry_count * 5, 60)

        if retry_count >= max_retries:
            status = "failed"
            next_attempt = None
        else:
            status = "queued"
            next_time = datetime.now(timezone.utc) + timedelta(
                minutes=backoff_minutes
            )
            next_attempt = next_time.isoformat()

        cursor.execute(
            """
            UPDATE job_queue
            SET status = ?, retry_count = ?, last_error = ?,
                next_attempt_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, retry_count, error_msg, next_attempt, now_utc(), job_id),
        )
        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error marking job failed: {str(e)}")


def log_push_result(
    job_id: int, response_code: int, response_body: str
) -> None:
    """Log push operation result."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO push_log (job_id, response_code, response_body, sent_at)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, response_code, response_body, now_utc()),
        )
        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error logging push result: {str(e)}")


def reset_stuck_jobs(timeout_minutes: int = 10) -> int:
    """
    Reset jobs stuck in processing.

    Args:
        timeout_minutes: Timeout threshold

    Returns:
        Number of jobs reset
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        timeout = datetime.now(timezone.utc) - timedelta(
            minutes=timeout_minutes
        )
        timeout_str = timeout.isoformat()

        cursor.execute(
            """
            UPDATE job_queue
            SET status = 'queued', updated_at = ?
            WHERE status = 'processing'
            AND last_attempt_at < ?
            """,
            (now_utc(), timeout_str),
        )
        count = cursor.rowcount
        conn.commit()
        conn.close()

        if count > 0:
            logger.warning(f"⚠️  Reset {count} stuck jobs")

        return count

    except Exception as e:
        logger.error(f"❌ Error resetting stuck jobs: {str(e)}")
        return 0
