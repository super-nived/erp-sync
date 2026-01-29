"""
Application startup and shutdown logic.

This module handles initialization tasks that should happen
when the application starts and cleanup when it shuts down.
"""

from app.core.logging import get_logger
from app.db.client import pb

logger = get_logger(__name__)


def init_job_sync_db() -> None:
    """Initialize job sync SQLite database."""
    try:
        from app.features.job_sync.db_schema import init_database

        init_database()
    except Exception as e:
        logger.error(f"❌ Failed to initialize job sync database: {e}")


def start_scheduler() -> None:
    """Start the ERP sync scheduler with initial sync."""
    try:
        from app.features.job_sync.scheduler import scheduler

        scheduler.start(run_immediately=True)
        logger.info("✅ ERP sync scheduler started with initial sync")
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")


def startup() -> None:
    """
    Execute startup tasks.

    - Authenticate with PocketBase
    - Initialize connections
    - Verify configuration
    """
    logger.info("Application startup")

    # Try to authenticate with PocketBase
    try:
        logger.info("Attempting PocketBase authentication...")
        pb.auth_admin()
        logger.info("✅ PocketBase authenticated successfully")
    except ConnectionError as e:
        logger.error(f"❌ PocketBase connection failed: {e}")
        logger.warning(
            "Application will start but PocketBase features won't work. "
            "Start PocketBase and restart the app."
        )
    except ValueError as e:
        logger.error(f"❌ PocketBase configuration error: {e}")
        logger.warning("Check your .env file for PB_ADMIN_EMAIL and PB_ADMIN_PASSWORD")
    except Exception as e:
        logger.error(f"❌ Unexpected error during PocketBase auth: {e}")

    init_job_sync_db()
    start_scheduler()
    logger.info("Application ready")


async def shutdown() -> None:
    """
    Execute shutdown tasks.

    - Close database connections
    - Cleanup resources
    - Stop scheduler
    """
    logger.info("Application shutdown")

    try:
        from app.features.job_sync.scheduler import scheduler

        await scheduler.stop()
        logger.info("✅ ERP sync scheduler stopped")
    except Exception as e:
        logger.error(f"❌ Failed to stop scheduler: {e}")
