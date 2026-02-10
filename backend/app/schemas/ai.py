"""
AI validation schemas.

Defines schemas for AI-based validation requests and responses.
Handles prompt data and validation results.
Does not contain invoice business logic or validation rules.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ValidationRequest(BaseModel):
    """AI validation request."""
    prompt: str = Field(..., description="Validation prompt")
    data: dict = Field(..., description="Data to validate")


class ValidationResponse(BaseModel):
    """AI validation response."""
    valid: bool = Field(..., description="Validation result")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    confidence: Optional[float] = Field(None, description="Validation confidence score")

