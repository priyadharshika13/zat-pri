"""
AI-powered root cause analysis schemas.

Defines schemas for AI-powered root cause analysis of ZATCA failures.
Handles root cause analysis requests with primary/secondary causes and prevention checklists.
Does not contain AI logic - delegates to AI service layer.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.constants import Environment


class RootCauseAnalysisRequest(BaseModel):
    """Request for AI-powered root cause analysis of ZATCA failure."""
    error_code: str = Field(..., description="ZATCA error code (e.g., 'ZATCA-2001')")
    error_message: Optional[str] = Field(None, description="Error message from ZATCA")
    rule_based_explanation: Optional[Dict[str, Any]] = Field(
        None,
        description="Rule-based explanation from error catalog (optional, enhances AI analysis)"
    )
    environment: Environment = Field(..., description="Target environment (SANDBOX or PRODUCTION)")


class RootCauseAnalysisResponse(BaseModel):
    """Response containing AI-powered root cause analysis results."""
    primary_cause: str = Field(..., description="Single dominant root cause of the failure")
    secondary_causes: List[str] = Field(default_factory=list, description="Supporting contributing factors")
    prevention_checklist: List[str] = Field(default_factory=list, description="Actionable steps to prevent recurrence")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")

