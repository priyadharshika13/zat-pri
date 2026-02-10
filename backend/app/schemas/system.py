"""
System health and status schemas.

Defines response schemas for system health checks and observability.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ZATCAHealthStatus(BaseModel):
    """ZATCA API health status."""
    status: str = Field(..., description="Connection status: CONNECTED, DISCONNECTED, ERROR")
    environment: str = Field(..., description="ZATCA environment: SANDBOX or PRODUCTION")
    last_checked: datetime = Field(..., description="Last health check timestamp (UTC)")
    error_message: Optional[str] = Field(None, description="Error message if status is not CONNECTED")


class AIHealthStatus(BaseModel):
    """AI provider (OpenRouter) health status."""
    status: str = Field(..., description="Status: ENABLED, DISABLED, ERROR")
    provider: str = Field(default="OpenRouter", description="AI provider name")
    error_message: Optional[str] = Field(None, description="Error message if status is ERROR")


class SystemHealthStatus(BaseModel):
    """Internal system health status."""
    uptime_seconds: int = Field(..., description="Application uptime in seconds")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Application environment: local, staging, production")


class SystemHealthResponse(BaseModel):
    """Complete system health response."""
    environment: str = Field(..., description="Overall environment: SANDBOX or PRODUCTION")
    zatca: ZATCAHealthStatus = Field(..., description="ZATCA API health status")
    ai: AIHealthStatus = Field(..., description="AI provider health status")
    system: SystemHealthStatus = Field(..., description="Internal system health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp (UTC)")

