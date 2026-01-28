"""
Application startup and shutdown logic.

This module handles initialization tasks that should happen
when the application starts and cleanup when it shuts down.
"""

from app.core.logging import get_logger
from app.db.client import pb

logger = get_logger(__name__)


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

    logger.info("Application ready")


def shutdown() -> None:
    """
    Execute shutdown tasks.

    - Close database connections
    - Cleanup resources
    """
    logger.info("Application shutdown")
