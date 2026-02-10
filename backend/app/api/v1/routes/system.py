"""
System health and observability API endpoints.

Provides system-level health checks for external services and internal status.
No authentication required - read-only, safe for monitoring.
"""

import logging
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from typing import Optional

import httpx

from app.core.config import get_settings
from app.schemas.system import SystemHealthResponse, ZATCAHealthStatus, AIHealthStatus, SystemHealthStatus
from app.services.ai.openrouter_service import get_openrouter_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])

# Track application start time for uptime calculation
_application_start_time: Optional[float] = None


def set_application_start_time():
    """Sets application start time (called on startup)."""
    global _application_start_time
    if _application_start_time is None:
        _application_start_time = time.time()


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System health check"
)
async def get_system_health() -> SystemHealthResponse:
    """
    Returns comprehensive system health status.
    
    **No authentication required** - safe for monitoring and status pages.
    
    **Health Checks:**
    1. ZATCA API - Real connectivity check (HEAD request)
    2. AI Provider (OpenRouter) - API key validation and lightweight test
    3. Internal System - Uptime, version, environment
    
    **Response Time:** < 2 seconds (with timeout controls)
    
    **Error Handling:** Never raises 500 errors - all failures reported as status
    """
    settings = get_settings()
    
    # Get ZATCA health status
    zatca_status = await _check_zatca_health(settings)
    
    # Get AI health status
    ai_status = await _check_ai_health(settings)
    
    # Get system health status
    system_status = _get_system_health(settings)
    
    # Determine overall environment
    overall_env = settings.zatca_environment
    
    return SystemHealthResponse(
        environment=overall_env,
        zatca=zatca_status,
        ai=ai_status,
        system=system_status,
        timestamp=datetime.utcnow()
    )


async def _check_zatca_health(settings) -> ZATCAHealthStatus:
    """
    Checks ZATCA API connectivity.
    
    Uses lightweight HEAD request to verify reachability.
    Never raises exceptions - returns status with error message if failed.
    """
    zatca_env = settings.zatca_environment
    base_url = settings.zatca_production_base_url if zatca_env == "PRODUCTION" else settings.zatca_sandbox_base_url
    
    try:
        # Use HEAD request for lightweight check (faster than GET)
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Try to reach the base URL (lightweight check)
            response = await client.head(base_url, follow_redirects=True)
            
            # If we get any response (even 404/401), the service is reachable
            status_code = response.status_code
            
            logger.debug(f"ZATCA health check: {zatca_env} - Status code: {status_code}")
            
            return ZATCAHealthStatus(
                status="CONNECTED",
                environment=zatca_env,
                last_checked=datetime.utcnow(),
                error_message=None
            )
            
    except httpx.TimeoutException:
        logger.warning(f"ZATCA health check timeout: {zatca_env}")
        return ZATCAHealthStatus(
            status="DISCONNECTED",
            environment=zatca_env,
            last_checked=datetime.utcnow(),
            error_message="Connection timeout"
        )
    
    except httpx.ConnectError as e:
        logger.warning(f"ZATCA health check connection error: {zatca_env} - {e}")
        return ZATCAHealthStatus(
            status="DISCONNECTED",
            environment=zatca_env,
            last_checked=datetime.utcnow(),
            error_message=f"Connection error: {str(e)[:100]}"
        )
    
    except Exception as e:
        logger.error(f"ZATCA health check error: {zatca_env} - {e}")
        return ZATCAHealthStatus(
            status="ERROR",
            environment=zatca_env,
            last_checked=datetime.utcnow(),
            error_message=f"Health check failed: {str(e)[:100]}"
        )


async def _check_ai_health(settings) -> AIHealthStatus:
    """
    Checks AI provider (OpenRouter) health.
    
    Validates API key presence and attempts lightweight validation.
    Never raises exceptions - returns status with error message if failed.
    """
    # Check if AI is globally disabled
    if not settings.enable_ai_explanation:
        return AIHealthStatus(
            status="DISABLED",
            provider="OpenRouter",
            error_message=None
        )
    
    # Check API key presence
    if not settings.openrouter_api_key:
        return AIHealthStatus(
            status="ERROR",
            provider="OpenRouter",
            error_message="API key not configured"
        )
    
    try:
        # Attempt lightweight validation by checking if service is initialized
        openrouter = get_openrouter_service()
        
        if not openrouter.api_key:
            return AIHealthStatus(
                status="ERROR",
                provider="OpenRouter",
                error_message="OpenRouter service not initialized"
            )
        
        # Try a minimal validation call (very lightweight)
        # We'll just check if we can make a request to the API
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Make a minimal request to validate connectivity
            # Using models endpoint as it's lightweight
            response = await client.get(
                f"{openrouter.base_url}/models",
                headers={
                    "Authorization": f"Bearer {openrouter.api_key}",
                    "HTTP-Referer": "https://zatca-api.com",
                    "X-Title": "ZATCA Compliance API"
                }
            )
            
            if response.status_code == 200:
                return AIHealthStatus(
                    status="ENABLED",
                    provider="OpenRouter",
                    error_message=None
                )
            elif response.status_code == 401:
                return AIHealthStatus(
                    status="ERROR",
                    provider="OpenRouter",
                    error_message="Invalid API key"
                )
            else:
                return AIHealthStatus(
                    status="ERROR",
                    provider="OpenRouter",
                    error_message=f"API returned status {response.status_code}"
                )
    
    except httpx.TimeoutException:
        logger.warning("OpenRouter health check timeout")
        return AIHealthStatus(
            status="ERROR",
            provider="OpenRouter",
            error_message="Connection timeout"
        )
    
    except httpx.HTTPStatusError as e:
        logger.warning(f"OpenRouter health check HTTP error: {e.response.status_code}")
        return AIHealthStatus(
            status="ERROR",
            provider="OpenRouter",
            error_message=f"HTTP {e.response.status_code}"
        )
    
    except Exception as e:
        logger.error(f"OpenRouter health check error: {e}")
        return AIHealthStatus(
            status="ERROR",
            provider="OpenRouter",
            error_message=f"Health check failed: {str(e)[:100]}"
        )


def _get_system_health(settings) -> SystemHealthStatus:
    """
    Gets internal system health status.
    
    Calculates uptime and returns system information.
    """
    global _application_start_time
    
    # Calculate uptime
    uptime_seconds = 0
    if _application_start_time:
        uptime_seconds = int(time.time() - _application_start_time)
    
    # Determine environment name
    env_name = settings.environment_name.lower()
    if env_name not in ["local", "staging", "production"]:
        env_name = "local"  # Default fallback
    
    return SystemHealthStatus(
        uptime_seconds=uptime_seconds,
        version=settings.app_version,
        environment=env_name
    )

