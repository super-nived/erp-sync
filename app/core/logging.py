import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.settings import settings

# Context variables for request tracking
request_id_ctx: ContextVar[str] = ContextVar("request_id", default=None)
request_context_ctx: ContextVar[Dict] = ContextVar("request_context", default={})


class StructuredFormatter(logging.Formatter):
    """
    JSON structured logging formatter.

    Outputs logs in machine-readable JSON format with all mandatory fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log structure
        log_data = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "service": settings.app_name,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request context if available
        request_id = request_id_ctx.get()
        if request_id:
            log_data["request_id"] = request_id

        context = request_context_ctx.get()
        if context:
            log_data.update(context)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from record
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class PlainFormatter(logging.Formatter):
    """Simple plain text formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as plain text."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        request_id = request_id_ctx.get()
        req_id_str = f"[{request_id}]" if request_id else ""

        return f"{timestamp} - {record.levelname} - {record.name}{req_id_str} - {record.getMessage()}"


def setup_logging():
    """
    Configure application logging with structured JSON format.

    Uses JSON logging in production, plain text in debug mode.
    """
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # Choose formatter based on environment
    if settings.debug:
        formatter = PlainFormatter()
    else:
        formatter = StructuredFormatter()

    # Configure root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logging.basicConfig(
        level=log_level,
        handlers=[handler],
        force=True,
    )

    # Reduce noise from third-party libraries
    # Always suppress httpx/httpcore verbose logs (we have custom logging in PocketBase client)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Suppress uvicorn logs in production only
    if not settings.debug:
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def set_request_context(request_id: str, context: Dict[str, Any] = None):
    """
    Set request context for structured logging.

    Args:
        request_id: Unique request identifier
        context: Additional context fields (method, path, client_ip, etc.)
    """
    request_id_ctx.set(request_id)
    if context:
        request_context_ctx.set(context)


def clear_request_context():
    """Clear request context after request completion."""
    request_id_ctx.set(None)
    request_context_ctx.set({})
