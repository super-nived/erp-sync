"""
Job Sync Scheduler

Scheduler wrapper for the sync worker.
Simplified to delegate to worker module.
"""

from app.core.logging import get_logger
from app.features.job_sync.worker import worker

logger = get_logger(__name__)


class SyncScheduler:
    """Scheduler facade for sync worker."""

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return worker.is_running

    @property
    def sync_in_progress(self) -> bool:
        """Check if sync is in progress (always delegate to worker)."""
        return worker.is_running

    def start(self, run_immediately: bool = False) -> None:
        """
        Start the scheduler/worker.

        Args:
            run_immediately: Run fetch immediately on start
        """
        worker.start(run_fetch_immediately=run_immediately)
        logger.info("Sync scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler/worker."""
        await worker.stop()
        logger.info("Sync scheduler stopped")


scheduler = SyncScheduler()
