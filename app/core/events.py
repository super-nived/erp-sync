"""
Application lifecycle events (lifespan context manager).

Handles startup and shutdown events using FastAPI's modern lifespan API.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import get_logger
from app.core.startup import shutdown, startup

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.

    Executes startup tasks on application start and
    cleanup tasks on application shutdown.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    logger.info("🚀 Starting ERP Sync service...")
    startup()
    logger.info("✅ ERP Sync service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down ERP Sync service...")
    shutdown()
    logger.info("✅ ERP Sync service stopped")
