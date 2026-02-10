"""
AI-powered invoice pre-check advisor schemas.

Defines schemas for AI-powered invoice pre-check advisor requests and responses.
Handles pre-check requests with warnings, risk fields, and advisory notes.
Does not contain AI logic - delegates to AI service layer.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field
from app.core.constants import Environment


class PrecheckAdvisorRequest(BaseModel):
    """Request for AI-powered invoice pre-check advisor."""
    invoice_payload: Dict[str, Any] = Field(..., description="Invoice payload (read-only, used only for risk analysis)")
    environment: Environment = Field(..., description="Target environment (SANDBOX or PRODUCTION)")


class PrecheckAdvisorResponse(BaseModel):
    """Response containing AI-powered invoice pre-check advisor results."""
    warnings: List[str] = Field(default_factory=list, description="List of human-readable warnings")
    risk_fields: List[str] = Field(default_factory=list, description="List of JSONPath-like strings pointing to risky fields")
    advisory_notes: str = Field(..., description="Short summary advisory note")
    risk_score: str = Field(default="UNKNOWN", description="Risk score: LOW, MEDIUM, HIGH, or UNKNOWN")
    advisory_summary: str = Field(default="", description="Short summary advisory note (alias for advisory_notes)")
    
    def model_post_init(self, __context) -> None:
        """Ensures advisory_summary is set from advisory_notes if not provided."""
        if not self.advisory_summary:
            self.advisory_summary = self.advisory_notes

