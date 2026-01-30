"""
Job Sync Service

Business logic for ERP data synchronization using job queue pattern.
Following spec.md and task.md: Fetch -> Store -> Queue -> Process.
Each function under 30 lines with single responsibility.
"""

from typing import Any

from app.core.logging import get_logger
from app.features.job_sync import db_helpers, repo
from app.features.job_sync.schema import ERPRecord

logger = get_logger(__name__)


def fetch_and_store_erp_data(from_date: str | None = None) -> dict[str, int]:
    """
    Fetch ERP data and store in SQLite.

    Args:
        from_date: Optional start date in YYYY-MM-DD format.
                   Only used if provided.

    Returns:
        Dict with counts of records stored and queued
    """
    try:
        if from_date:
            logger.info(f"Fetching ERP data from {from_date}")
        else:
            logger.info("Fetching ERP data (no date filter)")
        erp_records = repo.fetch_erp_data(from_date)

        stored_count = 0
        queued_count = 0

        for record in erp_records:
            if not validate_required_fields(record):
                logger.warning("⚠️  Skipping invalid record")
                continue

            payload_id, is_updated = repo.store_erp_record_in_sqlite(record)

            if payload_id:
                stored_count += 1
                job_id = db_helpers.create_job_for_payload(
                    payload_id, force_requeue=is_updated
                )
                if job_id:
                    queued_count += 1

        logger.info(f"✅ Stored {stored_count}, queued {queued_count} records")
        return {"stored": stored_count, "queued": queued_count}

    except Exception as e:
        logger.error(f"❌ Error fetching and storing data: {str(e)}")
        return {"stored": 0, "queued": 0}


def validate_required_fields(record: dict[str, Any]) -> bool:
    """
    Validate ERP record has required unique key fields.

    Args:
        record: ERP record dict

    Returns:
        True if valid, False otherwise
    """
    required = ["CUST_ORDER_ID", "CUST_ORDER_LINE_NO", "BOM_PART_ID"]
    return all(field in record and record[field] for field in required)


def process_queued_job(job: dict[str, Any]) -> bool:
    """
    Process a single queued job.

    Args:
        job: Job dict with id and payload

    Returns:
        True if successful, False otherwise
    """
    try:
        job_id = job["id"]
        payload = job["payload"]

        logger.info(f"Processing job {job_id}")

        pb_data = transform_to_pocketbase(payload)
        success = push_to_pocketbase(payload, pb_data)

        if success:
            db_helpers.mark_job_done(job_id)
            db_helpers.log_push_result(job_id, 200, "Success")
            logger.info(f"✅ Job {job_id} completed")
            return True
        else:
            error_msg = "Failed to push to PocketBase"
            db_helpers.mark_job_failed(job_id, error_msg)
            db_helpers.log_push_result(job_id, 500, error_msg)
            logger.error(f"❌ Job {job_id} failed: {error_msg}")
            return False

    except Exception as e:
        error_msg = f"Job processing error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        db_helpers.mark_job_failed(job["id"], error_msg)
        db_helpers.log_push_result(job["id"], 500, error_msg)
        return False


def transform_to_pocketbase(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Transform ERP payload to PocketBase format.

    Args:
        payload: Raw ERP payload

    Returns:
        Transformed dict
    """
    try:
        erp_record = ERPRecord(**payload)
        return erp_record.model_dump(mode="json", exclude_none=False)
    except Exception as e:
        logger.error(f"❌ Transform error: {str(e)}")
        raise


def push_to_pocketbase(
    payload: dict[str, Any], pb_data: dict[str, Any]
) -> bool:
    """
    Push data to PocketBase (upsert).

    Args:
        payload: Original ERP payload
        pb_data: Transformed PocketBase data

    Returns:
        True if successful, False otherwise
    """
    try:
        cust_order_id = payload["CUST_ORDER_ID"]
        line_no = str(payload["CUST_ORDER_LINE_NO"])
        part_id = payload["BOM_PART_ID"]

        existing = repo.find_existing_record(cust_order_id, line_no, part_id)

        if existing:
            repo.update_record(existing["id"], pb_data)
            logger.info(f"🔄 Updated {cust_order_id}-{line_no}-{part_id}")
        else:
            repo.create_record(pb_data)
            logger.info(f"➕ Created {cust_order_id}-{line_no}-{part_id}")

        return True

    except Exception as e:
        logger.error(f"Push to PocketBase failed: {str(e)}")
        return False


def process_all_queued_jobs() -> dict[str, int]:
    """
    Process all queued jobs.

    Returns:
        Dict with success and failure counts
    """
    success_count = 0
    failure_count = 0

    while True:
        job = db_helpers.get_next_queued_job()

        if not job:
            break

        if process_queued_job(job):
            success_count += 1
        else:
            failure_count += 1

    logger.info(f"Processed: {success_count} success, {failure_count} failed")
    return {"success": success_count, "failed": failure_count}
