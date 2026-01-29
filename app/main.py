"""
ERP Sync Application Entry Point

Responsibilities:
- Create FastAPI application instance
- Register API routers
- Register middlewares
- Register exception handlers
- Wire lifespan events

Following spec.md rules:
- No business logic
- No database queries
- No feature-specific code
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.events import lifespan
from app.features.job_sync.router import router as job_sync_router
from app.core.exceptions import AppException
from app.core.handlers import (
    app_exception_handler,
    general_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.middlewares.logging_middleware import RequestLoggingMiddleware

# Setup logging
setup_logging()


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="ERP Sync Service",
        description="ERP data synchronization service following MPS BE architecture",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Register middlewares (order matters - logging should be first)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register exception handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # Register API routers
    app.include_router(health_router)
    app.include_router(job_sync_router)

    return app


app = create_app()
