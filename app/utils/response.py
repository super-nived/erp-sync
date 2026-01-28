from typing import Any


def success(data: Any, message: str = "Success") -> dict:
    """
    Create a successful API response.

    Args:
        data: Response data
        message: Success message

    Returns:
        dict: Standardized success response
    """
    return {"success": True, "message": message, "data": data}


def error(message: str, error_detail: str | None = None) -> dict:
    """
    Create an error API response.

    Args:
        message: Error message
        error_detail: Additional error details (optional)

    Returns:
        dict: Standardized error response
    """
    response = {"success": False, "message": message}
    if error_detail:
        response["error"] = error_detail
    return response


def paginated_success(
    data: list, page: int, limit: int, total: int, message: str = "Success"
) -> dict:
    """
    Create a paginated success response.

    Args:
        data: List of items
        page: Current page number
        limit: Items per page
        total: Total number of items

    Returns:
        dict: Standardized paginated response
    """
    return {
        "success": True,
        "message": message,
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if limit > 0 else 0,
        },
    }
