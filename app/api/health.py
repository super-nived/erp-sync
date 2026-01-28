"""Health Check API - Service health monitoring."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """
    Health check endpoint.

    Returns service status and basic information.
    """
    return {
        "status": "healthy",
        "service": "erp-sync",
        "version": "1.0.0"
    }
