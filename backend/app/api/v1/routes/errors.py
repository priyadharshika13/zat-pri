"""
ZATCA error explanation API endpoints.

Handles error code lookup and explanation retrieval.
Uses rule-based error catalog with optional AI enhancement.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated

from app.core.security import verify_api_key_and_resolve_tenant
from app.schemas.auth import TenantContext
from typing import Annotated
from app.schemas.error import ErrorExplanationRequest, ErrorExplanationResponse
from app.integrations.zatca.error_catalog import (
    get_error_info,
    extract_error_code_from_message,
    get_all_error_codes
)
from app.ai.zatca_explainer import ZATCAErrorExplainer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/errors", tags=["errors"])


@router.post(
    "/explain",
    response_model=ErrorExplanationResponse,
    status_code=status.HTTP_200_OK,
    summary="Explain ZATCA error code"
)
async def explain_error(
    request: ErrorExplanationRequest,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)]
) -> ErrorExplanationResponse:
    """
    Explains a ZATCA error code with human-readable explanation and fix suggestions.
    
    This endpoint uses a rule-based error catalog to provide:
    - Human-readable explanation
    - Technical root cause
    - Suggested corrective action
    
    Optionally enhanced with AI (set use_ai=true) for:
    - Enhanced English explanation
    - Arabic explanation (set include_arabic=true)
    - Step-by-step fix guidance
    
    You can provide:
    - error_code: Direct ZATCA error code (e.g., "ZATCA-2001")
    - error_message: Error message that may contain error code (will be extracted)
    - error_response: Full ZATCA error response dictionary
    
    Returns error explanation from the catalog, or generic explanation if code not found.
    """
    error_code = None
    original_error = None
    
    # Determine error code from request
    if request.error_code:
        error_code = request.error_code.upper().strip()
    elif request.error_response:
        error_code = request.error_response.get("error_code")
        original_error = request.error_response.get("error") or request.error_response.get("error_message", "")
        if not error_code and original_error:
            extracted_code = extract_error_code_from_message(original_error)
            if extracted_code:
                error_code = extracted_code
    elif request.error_message:
        original_error = request.error_message
        # Try to extract error code from message
        extracted_code = extract_error_code_from_message(request.error_message)
        if extracted_code:
            error_code = extracted_code
        else:
            # If no code found, use generic unknown error
            error_code = "ZATCA-UNKNOWN"
    
    # Get error information from catalog
    error_info = get_error_info(error_code)
    
    if not error_info:
        # Fallback to unknown error if code not found
        error_info = get_error_info("ZATCA-UNKNOWN")
        if not error_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error catalog not properly initialized"
            )
    
    # Build base response from rule-based catalog
    response = ErrorExplanationResponse(
        error_code=error_code,
        original_error=original_error if original_error else None,
        human_explanation=error_info.get("explanation", "Unknown error"),
        technical_reason=error_info.get("technical_reason", "Error details not available"),
        fix_suggestion=error_info.get("corrective_action", "Review error and consult ZATCA documentation")
    )
    
    # Optionally enhance with AI explanation
    # CRITICAL: Check global AI toggle - AI is NEVER invoked if globally disabled
    if request.use_ai:
        from app.core.config import get_settings
        settings = get_settings()
        
        if not settings.enable_ai_explanation:
            logger.info(
                f"AI explanation requested but globally disabled (ENABLE_AI_EXPLANATION=false). "
                f"Falling back to rule-based explanation for error code: {error_code}"
            )
        else:
            try:
                explainer = ZATCAErrorExplainer()
                # Build error response dict for AI
                error_response_dict = {
                    "error_code": error_code,
                    "error": original_error or request.error_message or "",
                    "status": "REJECTED"
                }
                if request.error_response:
                    error_response_dict.update(request.error_response)
                
                ai_explanation = await explainer.explain_error(
                    error_response_dict,
                    include_arabic=request.include_arabic
                )
                
                # Add AI-enhanced fields
                response.ai_english_explanation = ai_explanation.get("english_explanation")
                response.ai_arabic_explanation = ai_explanation.get("arabic_explanation") if request.include_arabic else None
                response.ai_fix_steps = ai_explanation.get("fix_steps", [])
            except Exception as e:
                # Log error but don't fail - return rule-based explanation
                logger.warning(f"AI explanation failed, using rule-based: {e}")
    
    return response


@router.get(
    "/codes",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="List all available ZATCA error codes"
)
async def list_error_codes(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)]
) -> list[str]:
    """
    Returns list of all available ZATCA error codes in the catalog.
    
    Useful for discovering available error codes that can be explained.
    """
    return get_all_error_codes()

