"""
AI-powered error explanation schemas.

Defines schemas for AI-powered ZATCA error explanation requests and responses.
Handles AI explanation requests with English and Arabic outputs.
Does not contain AI logic - delegates to AI service layer.
"""

from typing import Optional
from pydantic import BaseModel, Field


class AIErrorExplanationRequest(BaseModel):
    """Request for AI-powered ZATCA error explanation."""
    error_code: Optional[str] = Field(None, description="ZATCA error code (e.g., 'ZATCA-2001')")
    error_message: Optional[str] = Field(None, description="Error message that may contain error code")
    error_response: Optional[dict] = Field(None, description="Full ZATCA error response dictionary")
    
    def model_post_init(self, __context) -> None:
        """Validates that at least one field is provided."""
        if not self.error_code and not self.error_message and not self.error_response:
            raise ValueError("Either error_code, error_message, or error_response must be provided")


class AIErrorExplanationResponse(BaseModel):
    """Response containing AI-powered ZATCA error explanation."""
    error_code: str = Field(..., description="ZATCA error code")
    explanation_en: str = Field(..., description="English explanation of the error")
    explanation_ar: str = Field(..., description="Arabic explanation of the error")
    recommended_steps: list[str] = Field(..., description="Step-by-step recommended fix actions")

