"""
AI-powered invoice rejection prediction schemas.

Defines schemas for AI-powered invoice rejection prediction requests and responses.
Handles prediction requests with risk assessment and advisory notes.
Does not contain AI logic - delegates to AI service layer.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.constants import Environment


class RejectionPredictionRequest(BaseModel):
    """Request for AI-powered invoice rejection prediction."""
    invoice_payload: Dict[str, Any] = Field(..., description="Invoice payload (read-only, used only for risk analysis)")
    environment: Environment = Field(..., description="Target environment (SANDBOX or PRODUCTION)")


class RejectionPredictionResponse(BaseModel):
    """Response containing AI-powered invoice rejection prediction."""
    risk_level: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH, or UNKNOWN")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    likely_reasons: List[str] = Field(default_factory=list, description="List of likely rejection reasons")
    advisory_note: str = Field(..., description="Short human-readable advisory message")

