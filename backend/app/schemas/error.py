"""
Error explanation schemas.

Defines schemas for ZATCA error explanation requests and responses.
Handles error code lookup and explanation retrieval.
Does not contain error catalog logic - delegates to error catalog module.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ErrorExplanationRequest(BaseModel):
    """Request for ZATCA error explanation."""
    error_code: Optional[str] = Field(None, description="ZATCA error code (e.g., 'ZATCA-2001')")
    error_message: Optional[str] = Field(None, description="Error message that may contain error code")
    error_response: Optional[dict] = Field(None, description="Full ZATCA error response dictionary")
    use_ai: bool = Field(False, description="Whether to use AI for enhanced explanation (requires OpenAI)")
    include_arabic: bool = Field(False, description="Include Arabic explanation (requires AI)")
    
    def model_post_init(self, __context) -> None:
        """Validates that at least one field is provided."""
        if not self.error_code and not self.error_message and not self.error_response:
            raise ValueError("Either error_code, error_message, or error_response must be provided")


class ErrorExplanationResponse(BaseModel):
    """Response containing ZATCA error explanation."""
    error_code: str = Field(..., description="ZATCA error code")
    original_error: Optional[str] = Field(None, description="Original error message if provided")
    human_explanation: str = Field(..., description="Human-readable explanation of the error")
    technical_reason: str = Field(..., description="Technical root cause of the error")
    fix_suggestion: str = Field(..., description="Suggested corrective action")
    # AI-enhanced fields (optional)
    ai_english_explanation: Optional[str] = Field(None, description="AI-generated English explanation")
    ai_arabic_explanation: Optional[str] = Field(None, description="AI-generated Arabic explanation")
    ai_fix_steps: Optional[list[str]] = Field(None, description="AI-generated step-by-step fix guidance")

