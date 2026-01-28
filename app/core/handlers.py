"""
Global exception handlers.

Converts exceptions into standardized JSON responses with proper status codes.
"""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.core.settings import settings
from app.utils.response import error

logger = get_logger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom application exceptions.

    Args:
        request: FastAPI request object
        exc: Application exception

    Returns:
        JSONResponse: Standardized error response
    """
    logger.error(f"AppException: {exc.message} (status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code, content=error(message=exc.message)
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: FastAPI request object
        exc: Validation exception

    Returns:
        JSONResponse: Standardized validation error response
    """
    logger.warning(f"Validation error: {exc.errors()}")

    # Only expose validation details in debug mode
    error_detail = str(exc.errors()) if settings.debug else None

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error(
            message="Invalid request parameters. Please check your input.",
            error_detail=error_detail
        ),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Args:
        request: FastAPI request object
        exc: Unexpected exception

    Returns:
        JSONResponse: Standardized server error response
    """
    logger.exception(f"Unexpected error: {str(exc)}")

    # Only expose technical error details in debug mode
    # In production, hide details to prevent information leakage
    error_detail = str(exc) if settings.debug else None

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error(
            message="An unexpected error occurred. Please contact support if the issue persists.",
            error_detail=error_detail
        ),
    )
