"""
Health check API endpoint.

Provides application health status and version information.
Handles basic health monitoring and status reporting.
Does not contain business logic or invoice processing.
"""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """Returns application health status."""
    settings = get_settings()
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment.value
    }

