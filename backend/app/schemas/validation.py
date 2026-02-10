"""
Invoice validation response schemas.

Defines schemas for validation results and feedback.
Handles structured validation responses with issues and suggestions.
Does not contain validation logic or business rules.
"""

from typing import List
from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """Individual validation issue."""
    field: str = Field(..., description="Field or area where issue was found")
    severity: str = Field(..., description="Issue severity: error or warning")
    message: str = Field(..., description="Issue description")
    suggestion: str = Field(..., description="Actionable correction suggestion")


class ValidationResponse(BaseModel):
    """Invoice validation response."""
    status: str = Field(..., description="Validation status: PASS or FAIL")
    issues: List[ValidationIssue] = Field(default_factory=list, description="List of detected problems")
    suggestions: List[str] = Field(default_factory=list, description="Concise actionable corrections")

