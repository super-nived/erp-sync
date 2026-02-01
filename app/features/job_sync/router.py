"""
Job Sync Router

API endpoints for ERP sync operations.
Following spec.md: HTTP handling only, delegates to service.
"""

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.features.job_sync.scheduler import scheduler
from app.features.job_sync.schema import SyncTriggerRequest
from app.features.job_sync.worker import calculate_from_date
from app.utils.response import success

logger = get_logger(__name__)

router = APIRouter(prefix="/job-sync", tags=["Job Sync"])


@router.post("/trigger")
async def trigger_sync(request: SyncTriggerRequest):
    """
    Manually trigger an ERP fetch (adds to queue).

    Args:
        request: Sync trigger request with optional from_date

    Returns:
        Fetch result
    """
    try:
        from app.features.job_sync import service

        # Use provided from_date, or calculate from settings
        from_date = request.from_date or calculate_from_date()

        import asyncio

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, service.fetch_and_store_erp_data, from_date
        )

        return success(
            data=result,
            message=f"Fetched and queued {result['queued']} records",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger sync: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_sync_status():
    """
    Get comprehensive sync status with statistics.

    Returns:
        Scheduler status, current sync info, and database statistics
    """
    try:
        from app.features.job_sync import db_helpers
        from app.features.job_sync.worker import worker

        # Get database statistics
        db_stats = db_helpers.get_sync_statistics()

        # Get current sync session info
        current_sync = worker.current_sync_stats.copy()

        # Build full API URL with query params
        api_url = current_sync.get("api_url")
        query_params = current_sync.get("query_params", {})
        full_api_url = None

        if api_url:
            if query_params:
                # Build query string
                query_str = "&".join(
                    [f"{k}={v}" for k, v in query_params.items()]
                )
                full_api_url = f"{api_url}?{query_str}"
            else:
                full_api_url = api_url

        status_data = {
            "scheduler_running": scheduler.is_running,
            "sync_in_progress": scheduler.sync_in_progress,
            "current_sync": {
                "is_syncing": current_sync.get("is_syncing", False),
                "total_fetched": current_sync.get("total_fetched", 0),
                "unique_records": current_sync.get("unique_records", 0),
                "queued_jobs": current_sync.get("queued_jobs", 0),
                "started_at": current_sync.get("started_at"),
                "api_url": api_url,
                "query_params": query_params,
                "full_api_url": full_api_url,
            },
            "database": {
                "total_unique_records": db_stats.get(
                    "total_unique_records", 0
                ),
                "jobs_queued": db_stats.get("jobs_queued", 0),
                "jobs_processing": db_stats.get("jobs_processing", 0),
                "jobs_done": db_stats.get("jobs_done", 0),
                "jobs_failed": db_stats.get("jobs_failed", 0),
                "last_fetch_at": db_stats.get("last_fetch_at"),
            },
        }
        return success(data=status_data, message="Sync status retrieved")

    except Exception as e:
        logger.error(f"Failed to get sync status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_sync():
    """
    Stop the sync scheduler.

    Returns:
        Stop operation result
    """
    try:
        if not scheduler.is_running:
            return success(
                data={"message": "Scheduler is already stopped"},
                message="Scheduler not running",
            )

        if scheduler.sync_in_progress:
            raise HTTPException(
                status_code=409,
                detail="Cannot stop while sync is in progress",
            )

        await scheduler.stop()

        return success(
            data={"scheduler_running": False},
            message="Scheduler stopped successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
