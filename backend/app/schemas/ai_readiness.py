"""
AI-powered ZATCA readiness score schemas.

Defines schemas for AI-powered tenant-level compliance health scoring.
Handles readiness score requests with score, status, risk factors, and improvement suggestions.
Does not contain AI logic - delegates to AI service layer.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ReadinessScoreResponse(BaseModel):
    """Response containing AI-powered ZATCA readiness score."""
    readiness_score: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Compliance readiness score (0-100), null if AI disabled"
    )
    status: str = Field(..., description="Readiness status: GREEN (80-100), AMBER (50-79), RED (0-49), or UNKNOWN")
    risk_factors: List[str] = Field(default_factory=list, description="List of identified risk factors")
    improvement_suggestions: List[str] = Field(default_factory=list, description="Actionable steps to improve readiness")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")

