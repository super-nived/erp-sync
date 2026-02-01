"""
Job Sync Worker

Background worker for processing queued jobs.
Handles fetch, queue, and processing with crash recovery.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from app.core.logging import get_logger
from app.core.settings import settings
from app.features.job_sync import db_helpers, service

logger = get_logger(__name__)


class SyncWorker:
    """Worker for ERP sync operations."""

    def __init__(self):
        self.is_running = False
        self.fetch_task: asyncio.Task | None = None
        self.process_task: asyncio.Task | None = None
        self.reaper_task: asyncio.Task | None = None

        # Current sync session statistics
        self.current_sync_stats = {
            "is_syncing": False,
            "total_fetched": 0,
            "unique_records": 0,
            "queued_jobs": 0,
            "started_at": None,
            "api_url": None,
            "query_params": {},
        }

    def start(self, run_fetch_immediately: bool = False) -> None:
        """
        Start worker tasks.

        Args:
            run_fetch_immediately: Run fetch immediately on start
        """
        if not self.is_running:
            self.is_running = True
            self.fetch_task = asyncio.create_task(
                self._fetch_loop(run_fetch_immediately)
            )
            self.process_task = asyncio.create_task(self._process_loop())
            self.reaper_task = asyncio.create_task(self._reaper_loop())
            logger.info("Sync worker started")

    async def stop(self) -> None:
        """Stop all worker tasks."""
        self.is_running = False

        for task in [self.fetch_task, self.process_task, self.reaper_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("Sync worker stopped")

    async def _fetch_loop(self, run_immediately: bool = False) -> None:
        """
        Fetch ERP data periodically.

        Args:
            run_immediately: Run immediately on start
        """
        if run_immediately:
            await self._run_fetch()

        while self.is_running:
            try:
                await asyncio.sleep(
                    settings.erp_sync_interval_minutes * 60
                )
                await self._run_fetch()
            except Exception as e:
                logger.error(f"❌ Fetch loop error: {str(e)}")
                await asyncio.sleep(60)

    async def _run_fetch(self) -> None:
        """Run fetch operation."""
        try:
            # Mark sync as started
            self.current_sync_stats["is_syncing"] = True
            self.current_sync_stats["started_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            from_date = calculate_from_date()

            # Capture API URL and params
            self.current_sync_stats["api_url"] = settings.erp_api_url
            query_params = {}
            if settings.erp_txn_type:
                query_params["txnType"] = settings.erp_txn_type
            if from_date:
                query_params["fromDate"] = from_date
            self.current_sync_stats["query_params"] = query_params

            if from_date:
                logger.info(f"📥 Fetching ERP data from {from_date}")
            else:
                logger.info("📥 Fetching ERP data (no date filter)")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, service.fetch_and_store_erp_data, from_date
            )

            # Update sync statistics
            self.current_sync_stats["total_fetched"] = result.get(
                "fetched", 0
            )
            self.current_sync_stats["unique_records"] = result.get(
                "stored", 0
            )
            self.current_sync_stats["queued_jobs"] = result.get("queued", 0)
            self.current_sync_stats["is_syncing"] = False

            logger.info(
                f"✅ Fetch complete: {result['stored']} stored, "
                f"{result['queued']} queued"
            )

        except Exception as e:
            self.current_sync_stats["is_syncing"] = False
            logger.error(f"❌ Fetch error: {str(e)}")

    async def _process_loop(self) -> None:
        """Process queued jobs continuously."""
        while self.is_running:
            try:
                await asyncio.sleep(5)
                await self._run_processing()
            except Exception as e:
                logger.error(f"❌ Process loop error: {str(e)}")
                await asyncio.sleep(10)

    async def _run_processing(self) -> None:
        """Run job processing."""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, service.process_all_queued_jobs
            )

            if result["success"] > 0 or result["failed"] > 0:
                logger.info(
                    f"⚙️  Processing complete: {result['success']} success, "
                    f"{result['failed']} failed"
                )

        except Exception as e:
            logger.error(f"❌ Processing error: {str(e)}")

    async def _reaper_loop(self) -> None:
        """Reset stuck jobs periodically."""
        while self.is_running:
            try:
                await asyncio.sleep(300)
                await self._run_reaper()
            except Exception as e:
                logger.error(f"❌ Reaper loop error: {str(e)}")
                await asyncio.sleep(60)

    async def _run_reaper(self) -> None:
        """Run reaper to reset stuck jobs."""
        try:
            loop = asyncio.get_event_loop()
            count = await loop.run_in_executor(
                None, db_helpers.reset_stuck_jobs, 10
            )

            if count > 0:
                logger.warning(f"⚠️  Reaper reset {count} stuck jobs")

        except Exception as e:
            logger.error(f"❌ Reaper error: {str(e)}")


def calculate_from_date() -> str | None:
    """
    Calculate from_date for sync based on settings.

    Returns:
        Date string in YYYY-MM-DD format, or None if no date filter configured
    """
    # Priority 1: Use explicit from_date if set
    if settings.erp_sync_from_date:
        return settings.erp_sync_from_date

    # Priority 2: Calculate from days_back if set
    if settings.erp_sync_days_back:
        from_date = datetime.now(timezone.utc) - timedelta(
            days=settings.erp_sync_days_back
        )
        return from_date.strftime("%Y-%m-%d")

    # Priority 3: No date filter configured
    return None


worker = SyncWorker()
