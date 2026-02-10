"""
AI-powered error trend intelligence schemas.

Defines schemas for AI-powered error and trend analysis.
Handles trend analysis requests with top errors, emerging risks, and recommendations.
Does not contain AI logic - delegates to AI service layer.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ErrorTrendItem(BaseModel):
    """Individual error trend item."""
    error_code: str = Field(..., description="ZATCA error code (e.g., 'ZATCA-2001')")
    count: int = Field(..., ge=0, description="Number of occurrences in the period")
    trend: str = Field(..., description="Trend direction: INCREASING, STABLE, or DECREASING")


class ErrorTrendsResponse(BaseModel):
    """Response containing AI-powered error trend analysis."""
    top_errors: List[ErrorTrendItem] = Field(default_factory=list, description="Top recurring errors with trend indicators")
    emerging_risks: List[str] = Field(default_factory=list, description="List of emerging compliance risks")
    trend_summary: str = Field(..., description="Short narrative summary of overall trends")
    recommended_actions: List[str] = Field(default_factory=list, description="Actionable steps based on trends")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")

