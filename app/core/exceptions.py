class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class UnauthorizedException(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message=message, status_code=401)


class ForbiddenException(AppException):
    """Raised when user lacks permission."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message=message, status_code=403)


class NotFoundException(AppException):
    """Raised when resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=404)


class BadRequestException(AppException):
    """Raised when request is invalid."""

    def __init__(self, message: str = "Bad request"):
        super().__init__(message=message, status_code=400)


class ConflictException(AppException):
    """Raised when resource conflict occurs."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message=message, status_code=409)


class ValidationException(AppException):
    """Raised when validation fails."""

    def __init__(self, message: str = "Validation error"):
        super().__init__(message=message, status_code=422)


class InternalServerException(AppException):
    """Raised when internal server error occurs."""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message=message, status_code=500)


class DatabaseException(AppException):
    """Raised when database/external service fails."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message=message, status_code=500)


class ExternalServiceException(AppException):
    """Raised when external service (PocketBase) fails."""

    def __init__(self, message: str = "External service error"):
        super().__init__(message=message, status_code=503)
