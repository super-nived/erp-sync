import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import clear_request_context, get_logger, set_request_context

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging.

    Logs all HTTP requests with mandatory fields:
    - timestamp
    - level
    - service
    - layer (always "middleware")
    - request_id
    - method
    - path
    - status_code
    - duration_ms
    - client_ip

    Log Levels:
    - INFO: Normal requests (200-299)
    - WARNING: Slow requests (>1s) or 3xx redirects
    - ERROR: Client/server errors (4xx/5xx)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log with structured format."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]

        # Extract client IP (handle proxies)
        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.headers.get("X-Real-IP")
            or request.client.host
            if request.client
            else "unknown"
        )

        # Set request context for all logs during this request
        request_context = {
            "layer": "middleware",
            "method": request.method,
            "path": request.url.path,
            "client_ip": client_ip,
        }
        set_request_context(request_id, request_context)

        # Store request_id in request state for access in routes
        request.state.request_id = request_id

        # Log request start (DEBUG level - only in development)
        logger.debug(f"Request started: {request.method} {request.url.path}")

        # Process request and measure time
        start_time = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)

        # Add request_id to response headers
        response.headers["X-Request-ID"] = request_id

        # Determine log level based on status code and duration
        status_code = response.status_code
        log_level = self._get_log_level(status_code, duration_ms)

        # Prepare log data
        log_message = f"{request.method} {request.url.path} - {status_code} ({duration_ms}ms)"

        # Log with appropriate level
        log_data = {
            "status_code": status_code,
            "duration_ms": duration_ms,
        }

        if log_level == "INFO":
            logger.info(log_message, extra={"extra_fields": log_data})
        elif log_level == "WARNING":
            logger.warning(log_message, extra={"extra_fields": log_data})
        elif log_level == "ERROR":
            logger.error(log_message, extra={"extra_fields": log_data})

        # Clear request context
        clear_request_context()

        return response

    def _get_log_level(self, status_code: int, duration_ms: int) -> str:
        """
        Determine log level based on status code and duration.

        Rules:
        - DEBUG: Headers, internal flow (dev only)
        - INFO: Successful requests (200-299)
        - WARNING: Slow requests (>1000ms) or redirects (3xx)
        - ERROR: Client/server errors (4xx/5xx)
        """
        # Errors take precedence
        if status_code >= 500:
            return "ERROR"
        if status_code >= 400:
            return "ERROR"

        # Slow requests
        if duration_ms > 1000:
            return "WARNING"

        # Redirects
        if 300 <= status_code < 400:
            return "WARNING"

        # Success
        return "INFO"
