"""
Job Sync Router

API endpoints for ERP sync operations.
Following spec.md: HTTP handling only, delegates to service.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.features.job_sync.scheduler import scheduler
from app.features.job_sync.schema import SyncTriggerRequest
from app.utils.response import success

logger = get_logger(__name__)

router = APIRouter(prefix="/job-sync", tags=["Job Sync"])


def get_default_from_date() -> str:
    """Get default from_date (7 days back)."""
    from_date = datetime.now(timezone.utc) - timedelta(days=365)
    return from_date.strftime("%Y-%m-%d")


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

        from_date = request.from_date or get_default_from_date()

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
    Get current sync scheduler status.

    Returns:
        Scheduler status information
    """
    try:
        status_data = {
            "scheduler_running": scheduler.is_running,
            "sync_in_progress": scheduler.sync_in_progress,
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
