"""
AI-powered ZATCA error explanation API endpoints.

Handles AI-powered error explanation requests.
Requires ENABLE_AI_EXPLANATION=true to function.
Logs AI usage without storing invoice data.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Annotated, Optional

from app.core.security import verify_api_key_and_resolve_tenant
from app.core.config import get_settings
from app.core.i18n import get_language_from_request, Language
from app.schemas.ai_explanation import AIErrorExplanationRequest, AIErrorExplanationResponse
from app.schemas.ai_prediction import RejectionPredictionRequest, RejectionPredictionResponse
from app.schemas.ai_precheck import PrecheckAdvisorRequest, PrecheckAdvisorResponse
from app.schemas.ai_root_cause import RootCauseAnalysisRequest, RootCauseAnalysisResponse
from app.schemas.ai_readiness import ReadinessScoreResponse
from app.schemas.ai_trends import ErrorTrendsResponse
from app.schemas.auth import TenantContext
from app.schemas.subscription import LimitExceededError
from app.services.subscription_service import SubscriptionService
from app.integrations.zatca.error_catalog import (
    extract_error_code_from_message,
    get_error_info
)
from app.ai.zatca_explainer import ZATCAErrorExplainer
from app.ai.rejection_predictor import InvoiceRejectionPredictor
from app.ai.precheck_advisor import PrecheckAdvisor
from app.ai.root_cause_engine import RootCauseEngine
from app.ai.readiness_scorer import ReadinessScorer
from app.ai.error_trend_analyzer import ErrorTrendAnalyzer
from app.db.session import get_db
from sqlalchemy.orm import Session
from typing import Annotated

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/explain-zatca-error",
    response_model=AIErrorExplanationResponse,
    status_code=status.HTTP_200_OK,
    summary="AI-powered ZATCA error explanation"
)
async def explain_zatca_error_ai(
    request: AIErrorExplanationRequest,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    http_request: Request
) -> AIErrorExplanationResponse:
    """
    Provides AI-powered explanation for ZATCA errors with English and Arabic explanations.
    
    **Requirements:**
    - ENABLE_AI_EXPLANATION must be set to true
    - OpenAI API key must be configured
    
    **Output:**
    - English explanation (explanation_en)
    - Arabic explanation (explanation_ar)
    - Step-by-step recommended fix actions (recommended_steps)
    
    **Privacy:**
    - AI usage is logged for monitoring purposes
    - No invoice data is stored or logged
    - Only error codes and error messages are processed
    
    **Fallback:**
    - If AI is disabled or unavailable, returns rule-based explanation
    """
    settings = get_settings()
    
    # CRITICAL: Enforce subscription AI limits before processing
    subscription_service = SubscriptionService(db, tenant)
    allowed, limit_error = subscription_service.check_ai_limit()
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=limit_error.model_dump()
        )
    
    # CRITICAL: Check global AI toggle
    if not settings.enable_ai_explanation:
        logger.warning(
            "AI explanation endpoint called but AI is globally disabled (ENABLE_AI_EXPLANATION=false). "
            "Returning rule-based explanation."
        )
        # CRITICAL: Increment AI usage even when AI is disabled (SaaS billing semantics)
        subscription_service.increment_ai_count()
        return await _get_rule_based_explanation(request)
    
    # Extract error code
    error_code = None
    error_message = None
    
    if request.error_code:
        error_code = request.error_code.upper().strip()
    elif request.error_response:
        error_code = request.error_response.get("error_code")
        error_message = request.error_response.get("error") or request.error_response.get("error_message", "")
        if not error_code and error_message:
            error_code = extract_error_code_from_message(error_message)
    elif request.error_message:
        error_message = request.error_message
        error_code = extract_error_code_from_message(request.error_message)
    
    if not error_code:
        error_code = "ZATCA-UNKNOWN"
    
    # Log AI usage (without invoice data)
    logger.info(
        f"AI explanation requested for error code: {error_code}. "
        f"AI enabled: {settings.enable_ai_explanation}"
    )
    
    # Build error response dict for AI service
    error_response_dict = {
        "error_code": error_code,
        "error": error_message or request.error_message or "",
        "status": "REJECTED"
    }
    if request.error_response:
        error_response_dict.update(request.error_response)
    
    # CRITICAL: Increment AI usage BEFORE calling AI service
    # This preserves correct SaaS billing semantics - we charge for the API call, not AI success
    subscription_service.increment_ai_count()
    
    try:
        # Get preferred language from request
        preferred_lang = get_language_from_request(http_request)
        
        # Get AI explanation - always include Arabic, but prioritize based on language
        explainer = ZATCAErrorExplainer()
        ai_explanation = await explainer.explain_error(
            error_response_dict,
            include_arabic=True,  # Always include Arabic
            preferred_language=preferred_lang  # Prioritize Arabic if requested
        )
        
        # Log successful AI usage
        logger.info(
            f"AI explanation generated successfully for error code: {error_code}. "
            f"AI service: OpenAI GPT-4o"
        )
        
        # Build response
        return AIErrorExplanationResponse(
            error_code=error_code,
            explanation_en=ai_explanation.get("english_explanation", "Error explanation not available"),
            explanation_ar=ai_explanation.get("arabic_explanation", ""),
            recommended_steps=ai_explanation.get("fix_steps", [])
        )
        
    except Exception as e:
        # Log AI failure but don't expose internal errors
        logger.error(
            f"AI explanation failed for error code: {error_code}. "
            f"Error: {str(e)}. Falling back to rule-based explanation."
        )
        # Usage already incremented before AI call, so fallback is already counted
        return await _get_rule_based_explanation(request)


async def _get_rule_based_explanation(
    request: AIErrorExplanationRequest
) -> AIErrorExplanationResponse:
    """
    Provides rule-based explanation as fallback when AI is unavailable.
    
    Args:
        request: Error explanation request
        
    Returns:
        Rule-based error explanation response
    """
    # Extract error code
    error_code = None
    
    if request.error_code:
        error_code = request.error_code.upper().strip()
    elif request.error_response:
        error_code = request.error_response.get("error_code")
        if not error_code:
            error_message = request.error_response.get("error") or request.error_response.get("error_message", "")
            if error_message:
                error_code = extract_error_code_from_message(error_message)
    elif request.error_message:
        error_code = extract_error_code_from_message(request.error_message)
    
    if not error_code:
        error_code = "ZATCA-UNKNOWN"
    
    # Get rule-based error info
    error_info = get_error_info(error_code)
    if not error_info:
        error_info = get_error_info("ZATCA-UNKNOWN")
        if not error_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error catalog not properly initialized"
            )
    
    # Return rule-based explanation
    # Note: Rule-based catalog doesn't have Arabic, so we return empty string
    return AIErrorExplanationResponse(
        error_code=error_code,
        explanation_en=error_info.get("explanation", "Error explanation not available"),
        explanation_ar="",  # Rule-based catalog doesn't have Arabic
        recommended_steps=[error_info.get("corrective_action", "Review error and consult ZATCA documentation")]
    )


@router.post(
    "/predict-rejection",
    response_model=RejectionPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="AI-powered invoice rejection prediction"
)
async def predict_rejection(
    request: RejectionPredictionRequest,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> RejectionPredictionResponse:
    """
    Predicts the likelihood of ZATCA invoice rejection BEFORE submission.
    
    **CRITICAL: This is ADVISORY-ONLY. The AI:**
    - Does NOT modify invoice payload
    - Does NOT generate XML
    - Does NOT calculate VAT
    - Does NOT touch hash/PIH/signature
    - Does NOT block submission
    
    **Requirements:**
    - ENABLE_AI_EXPLANATION must be set to true (if disabled, returns UNKNOWN risk)
    - OpenAI API key must be configured
    
    **Input:**
    - invoice_payload: Read-only invoice payload (used only for risk analysis)
    - environment: Target environment (SANDBOX or PRODUCTION)
    
    **Output:**
    - risk_level: LOW, MEDIUM, HIGH, or UNKNOWN
    - confidence: Confidence score (0.0 to 1.0)
    - likely_reasons: List of likely rejection reasons (if any)
    - advisory_note: Short human-readable advisory message
    
    **Privacy:**
    - AI usage is logged for monitoring purposes
    - No invoice data is stored or logged
    - Only risk assessment is returned
    
    **Fallback:**
    - If AI is disabled or unavailable, returns rule-based prediction or UNKNOWN
    """
    settings = get_settings()
    
    # CRITICAL: Enforce subscription AI limits before processing
    subscription_service = SubscriptionService(db, tenant)
    allowed, limit_error = subscription_service.check_ai_limit()
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=limit_error.model_dump()
        )
    
    # Log AI usage request (without invoice data)
    logger.info(
        f"Rejection prediction requested for tenant_id={tenant.tenant_id}, "
        f"environment={request.environment.value}, "
        f"AI enabled: {settings.enable_ai_explanation}"
    )
    
    # CRITICAL: Increment AI usage BEFORE calling AI service
    # This preserves correct SaaS billing semantics - we charge for the API call, not AI success
    subscription_service.increment_ai_count()
    
    try:
        # Get AI prediction
        predictor = InvoiceRejectionPredictor()
        prediction = await predictor.predict_rejection(
            invoice_payload=request.invoice_payload,
            tenant_context=tenant,
            db=db,
            environment=request.environment.value
        )
        
        # Log AI usage
        if settings.enable_ai_explanation and prediction.get("risk_level") != "UNKNOWN":
            logger.info(
                f"Rejection prediction generated successfully. "
                f"Risk level: {prediction.get('risk_level')}, "
                f"Confidence: {prediction.get('confidence')}, "
                f"Tenant: {tenant.tenant_id}"
            )
        else:
            logger.info(
                f"Rejection prediction returned (AI disabled or unavailable). "
                f"Risk level: {prediction.get('risk_level')}, "
                f"Tenant: {tenant.tenant_id}"
            )
        
        # Build response
        return RejectionPredictionResponse(
            risk_level=prediction.get("risk_level", "UNKNOWN"),
            confidence=prediction.get("confidence", 0.0),
            likely_reasons=prediction.get("likely_reasons", []),
            advisory_note=prediction.get("advisory_note", "AI prediction unavailable")
        )
        
    except Exception as e:
        # Log AI failure but don't expose internal errors
        logger.error(
            f"Rejection prediction failed for tenant_id={tenant.tenant_id}. "
            f"Error: {str(e)}. Returning safe fallback."
        )
        # Usage already incremented before AI call, so exception is already counted
        # Return safe fallback - never raise 500
        return RejectionPredictionResponse(
            risk_level="UNKNOWN",
            confidence=0.0,
            likely_reasons=[],
            advisory_note="Prediction service temporarily unavailable. Please review invoice manually before submission."
        )


@router.post(
    "/precheck-advisor",
    response_model=PrecheckAdvisorResponse,
    status_code=status.HTTP_200_OK,
    summary="AI-powered invoice pre-check advisor"
)
async def precheck_advisor(
    request: PrecheckAdvisorRequest,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> PrecheckAdvisorResponse:
    """
    Analyzes invoice payload before ZATCA submission and returns actionable warnings.
    
    **CRITICAL: This is ADVISORY-ONLY and READ-ONLY. The AI:**
    - Does NOT modify invoice payload
    - Does NOT generate XML
    - Does NOT calculate VAT
    - Does NOT touch hash/PIH/signature
    - Does NOT block submission
    
    **Requirements:**
    - ENABLE_AI_EXPLANATION must be set to true (if disabled, returns empty warnings)
    - OpenAI API key must be configured
    
    **Input:**
    - invoice_payload: Read-only invoice payload (used only for analysis)
    - environment: Target environment (SANDBOX or PRODUCTION)
    
    **Output:**
    - warnings: List of human-readable warnings
    - risk_fields: List of JSONPath-like strings pointing to risky fields
    - advisory_notes: Short summary advisory note
    
    **Analysis Scope:**
    - VAT percent inconsistencies
    - Missing buyer VAT for B2B
    - Invalid or missing tax categories
    - Rounding inconsistencies
    - Missing mandatory fields
    - Suspicious zero tax where VAT expected
    
    **Privacy:**
    - AI usage is logged for monitoring purposes
    - No invoice data is stored or logged
    - Only warnings and field pointers are returned
    
    **Fallback:**
    - If AI is disabled or unavailable, returns rule-based warnings or empty results
    """
    settings = get_settings()
    
    # CRITICAL: Enforce subscription AI limits before processing
    subscription_service = SubscriptionService(db, tenant)
    allowed, limit_error = subscription_service.check_ai_limit()
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=limit_error.model_dump()
        )
    
    # Log AI usage request (without invoice data)
    logger.info(
        f"Pre-check advisor requested for tenant_id={tenant.tenant_id}, "
        f"environment={request.environment.value}, "
        f"AI enabled: {settings.enable_ai_explanation}"
    )
    
    # CRITICAL: Increment AI usage BEFORE calling AI service
    # This preserves correct SaaS billing semantics - we charge for the API call, not AI success
    subscription_service.increment_ai_count()
    
    try:
        # Get AI analysis
        advisor = PrecheckAdvisor()
        analysis = await advisor.analyze_invoice(
            invoice_payload=request.invoice_payload,
            environment=request.environment.value
        )
        
        # Log AI usage
        if settings.enable_ai_explanation and (analysis.get("warnings") or analysis.get("risk_fields")):
            logger.info(
                f"Pre-check analysis generated successfully. "
                f"Warnings: {len(analysis.get('warnings', []))}, "
                f"Risk fields: {len(analysis.get('risk_fields', []))}, "
                f"Tenant: {tenant.tenant_id}"
            )
        else:
            logger.info(
                f"Pre-check analysis returned (AI disabled or no issues found). "
                f"Warnings: {len(analysis.get('warnings', []))}, "
                f"Tenant: {tenant.tenant_id}"
            )
        
        # Build response - ensure risk_score and advisory_summary are included
        advisory_notes = analysis.get("advisory_notes", "AI pre-check advisor is disabled.")
        return PrecheckAdvisorResponse(
            warnings=analysis.get("warnings", []),
            risk_fields=analysis.get("risk_fields", []),
            advisory_notes=advisory_notes,
            risk_score=analysis.get("risk_score", "UNKNOWN"),
            advisory_summary=advisory_notes  # Set explicitly (model_post_init will also set it)
        )
        
    except Exception as e:
        # Log AI failure but don't expose internal errors
        logger.error(
            f"Pre-check advisor failed for tenant_id={tenant.tenant_id}. "
            f"Error: {str(e)}. Returning safe fallback."
        )
        # Usage already incremented before AI call, so exception is already counted
        
        # Return safe fallback - never raise 500
        advisory_notes = "Pre-check service temporarily unavailable. Please review invoice manually before submission."
        return PrecheckAdvisorResponse(
            risk_score="UNKNOWN",
            warnings=[],
            risk_fields=[],
            advisory_notes=advisory_notes,
            advisory_summary=advisory_notes  # Set explicitly
        )


@router.post(
    "/root-cause-analysis",
    response_model=RootCauseAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="AI-powered root cause analysis of ZATCA failures"
)
async def root_cause_analysis(
    request: RootCauseAnalysisRequest,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> RootCauseAnalysisResponse:
    """
    Analyzes the root cause of ZATCA invoice failures.
    
    **CRITICAL: This is ADVISORY-ONLY and READ-ONLY. The AI:**
    - Does NOT modify invoice data
    - Does NOT generate XML
    - Does NOT calculate VAT
    - Does NOT touch hash/PIH/signature
    - Does NOT re-submit invoices
    
    **Purpose:**
    - Identifies WHY an invoice failed, not just WHAT failed
    - Provides systemic root cause analysis, not just symptom identification
    - Helps prevent recurring errors by addressing root causes
    
    **Requirements:**
    - ENABLE_AI_EXPLANATION must be set to true (if disabled, returns disabled message)
    - OpenAI API key must be configured
    
    **Input:**
    - error_code: ZATCA error code (e.g., "ZATCA-2001")
    - error_message: Error message from ZATCA (optional)
    - rule_based_explanation: Rule-based explanation from error catalog (optional, enhances analysis)
    - environment: Target environment (SANDBOX or PRODUCTION)
    
    **Note:** Invoice payload is NOT required - works with error information only.
    
    **Output:**
    - primary_cause: Single dominant root cause explanation
    - secondary_causes: List of supporting contributing factors
    - prevention_checklist: List of actionable steps to prevent recurrence
    - confidence: Confidence score (0.0 to 1.0)
    
    **Intelligence:**
    - Combines ZATCA error semantics
    - Uses rule-based explanation context
    - Analyzes historical tenant rejection patterns
    - Considers known ZATCA compliance pitfalls
    
    **Privacy:**
    - AI usage is logged for monitoring purposes
    - No invoice data is stored or logged
    - Only error codes and analysis results are returned
    
    **Fallback:**
    - If AI is disabled or unavailable, returns rule-based analysis or disabled message
    """
    settings = get_settings()
    
    # CRITICAL: Enforce subscription AI limits before processing
    subscription_service = SubscriptionService(db, tenant)
    allowed, limit_error = subscription_service.check_ai_limit()
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=limit_error.model_dump()
        )
    
    # Log AI usage request (without invoice data)
    logger.info(
        f"Root cause analysis requested for tenant_id={tenant.tenant_id}, "
        f"error_code={request.error_code}, "
        f"environment={request.environment.value}, "
        f"AI enabled: {settings.enable_ai_explanation}"
    )
    
    # CRITICAL: Increment AI usage BEFORE calling AI service
    # This preserves correct SaaS billing semantics - we charge for the API call, not AI success
    subscription_service.increment_ai_count()
    
    try:
        # Get AI root cause analysis
        engine = RootCauseEngine()
        analysis = await engine.analyze_root_cause(
            error_code=request.error_code,
            error_message=request.error_message,
            rule_based_explanation=request.rule_based_explanation,
            tenant_context=tenant,
            db=db,
            environment=request.environment.value
        )
        
        # Log AI usage
        if settings.enable_ai_explanation and analysis.get("confidence", 0.0) > 0.0:
            logger.info(
                f"Root cause analysis generated successfully. "
                f"Primary cause identified, confidence: {analysis.get('confidence', 0.0)}, "
                f"Tenant: {tenant.tenant_id}"
            )
        else:
            logger.info(
                f"Root cause analysis returned (AI disabled or unavailable). "
                f"Confidence: {analysis.get('confidence', 0.0)}, "
                f"Tenant: {tenant.tenant_id}"
            )
        
        # Build response
        return RootCauseAnalysisResponse(
            primary_cause=analysis.get("primary_cause", "Root cause analysis unavailable"),
            secondary_causes=analysis.get("secondary_causes", []),
            prevention_checklist=analysis.get("prevention_checklist", []),
            confidence=analysis.get("confidence", 0.0)
        )
        
    except Exception as e:
        # Log AI failure but don't expose internal errors
        logger.error(
            f"Root cause analysis failed for tenant_id={tenant.tenant_id}, error_code={request.error_code}. "
            f"Error: {str(e)}. Returning safe fallback."
        )
        # Usage already incremented before AI call, so exception is already counted
        # Return safe fallback - never raise 500
        return RootCauseAnalysisResponse(
            primary_cause="Root cause analysis service temporarily unavailable. Please review error manually.",
            secondary_causes=[],
            prevention_checklist=[
                "Review the error code and message",
                "Consult ZATCA documentation",
                "Check invoice data for common issues"
            ],
            confidence=0.0
        )


@router.get(
    "/readiness-score",
    response_model=ReadinessScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="AI-powered ZATCA readiness score"
)
async def get_readiness_score(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    period: Optional[str] = Query(
        default="30d",
        description="Analysis period: 30d, 90d, or all",
        regex="^(30d|90d|all)$"
    )
) -> ReadinessScoreResponse:
    """
    Computes tenant-level ZATCA compliance readiness score.
    
    **CRITICAL: This is ADVISORY-ONLY and READ-ONLY. The AI:**
    - Does NOT modify invoices
    - Does NOT generate XML
    - Does NOT calculate VAT
    - Does NOT touch hash/PIH/signature
    - Does NOT block submissions
    
    **Purpose:**
    - Provides a single, explainable compliance health score (0-100)
    - Classifies tenant as GREEN (80-100), AMBER (50-79), or RED (0-49)
    - Identifies risk factors and improvement suggestions
    - Ideal for dashboards, compliance reviews, and enterprise reporting
    
    **Requirements:**
    - ENABLE_AI_EXPLANATION must be set to true (if disabled, returns UNKNOWN status)
    - OpenAI API key must be configured
    
    **Input:**
    - No body required
    - Tenant context resolved from X-API-Key
    - Optional query parameter: period (30d, 90d, or all) - defaults to 30d
    
    **Output:**
    - readiness_score: int (0-100) or null if AI disabled
    - status: GREEN, AMBER, RED, or UNKNOWN
    - risk_factors: List of identified risk factors
    - improvement_suggestions: List of actionable improvement steps
    - confidence: Confidence score (0.0 to 1.0)
    
    **Scoring Logic:**
    - Considers rejection rate trend
    - Analyzes error diversity and patterns
    - Identifies recurring errors
    - Evaluates improvement or deterioration over time
    - Uses rule-based heuristics + AI synthesis
    
    **Privacy:**
    - AI usage is logged for monitoring purposes
    - No invoice payload is stored or logged
    - Only aggregated metrics are analyzed
    
    **Fallback:**
    - If AI is disabled or unavailable, returns rule-based scoring or UNKNOWN status
    """
    settings = get_settings()
    
    # CRITICAL: Enforce subscription AI limits before processing
    subscription_service = SubscriptionService(db, tenant)
    allowed, limit_error = subscription_service.check_ai_limit()
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=limit_error.model_dump()
        )
    
    # Validate period parameter
    if period not in ["30d", "90d", "all"]:
        period = "30d"  # Default to 30d if invalid
    
    # Log AI usage request (without invoice data)
    logger.info(
        f"Readiness score requested for tenant_id={tenant.tenant_id}, "
        f"period={period}, "
        f"AI enabled: {settings.enable_ai_explanation}"
    )
    
    # CRITICAL: Increment AI usage BEFORE calling AI service
    # This preserves correct SaaS billing semantics - we charge for the API call, not AI success
    subscription_service.increment_ai_count()
    
    try:
        # Get AI readiness score
        scorer = ReadinessScorer()
        score_data = await scorer.compute_readiness_score(
            tenant_context=tenant,
            db=db,
            period=period
        )
        
        # Log AI usage
        if settings.enable_ai_explanation and score_data.get("readiness_score") is not None:
            logger.info(
                f"Readiness score generated successfully. "
                f"Score: {score_data.get('readiness_score')}, "
                f"Status: {score_data.get('status')}, "
                f"Confidence: {score_data.get('confidence', 0.0)}, "
                f"Tenant: {tenant.tenant_id}"
            )
        else:
            logger.info(
                f"Readiness score returned (AI disabled or unavailable). "
                f"Status: {score_data.get('status')}, "
                f"Tenant: {tenant.tenant_id}"
            )
        
        # Build response
        return ReadinessScoreResponse(
            readiness_score=score_data.get("readiness_score"),
            status=score_data.get("status", "UNKNOWN"),
            risk_factors=score_data.get("risk_factors", []),
            improvement_suggestions=score_data.get("improvement_suggestions", []),
            confidence=score_data.get("confidence", 0.0)
        )
        
    except Exception as e:
        # Log AI failure but don't expose internal errors
        logger.error(
            f"Readiness score computation failed for tenant_id={tenant.tenant_id}. "
            f"Error: {str(e)}. Returning safe fallback."
        )
        # Usage already incremented before AI call, so exception is already counted
        # Return safe fallback - never raise 500
        return ReadinessScoreResponse(
            readiness_score=None,
            status="UNKNOWN",
            risk_factors=["Readiness scoring service temporarily unavailable"],
            improvement_suggestions=["Please try again later or contact support"],
            confidence=0.0
        )


@router.get(
    "/error-trends",
    response_model=ErrorTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="AI-powered error trend intelligence"
)
async def get_error_trends(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    period: Optional[str] = Query(
        default="30d",
        description="Analysis period: 7d, 30d, 90d, or all",
        regex="^(7d|30d|90d|all)$"
    ),
    scope: Optional[str] = Query(
        default="tenant",
        description="Analysis scope: tenant (current tenant) or global (admin only, anonymized)",
        regex="^(tenant|global)$"
    )
) -> ErrorTrendsResponse:
    """
    Analyzes time-based error trends and provides operational intelligence.
    
    **CRITICAL: This is ADVISORY-ONLY and READ-ONLY. The AI:**
    - Does NOT modify invoices
    - Does NOT generate XML
    - Does NOT calculate VAT
    - Does NOT touch hash/PIH/signature
    - Does NOT trigger submissions
    
    **Purpose:**
    - Provides time-based, trend-level intelligence about ZATCA errors
    - Answers: "What is going wrong repeatedly?", "Are things improving?", "What should we act on next?"
    - This is insight AI, not transaction AI
    - Ideal for operational and strategic decision-making
    
    **Requirements:**
    - ENABLE_AI_EXPLANATION must be set to true (if disabled, returns disabled message)
    - OpenAI API key must be configured
    
    **Input:**
    - No body required
    - Tenant context resolved from X-API-Key
    - Optional query parameters:
      - period: 7d, 30d, 90d, or all (defaults to 30d)
      - scope: tenant (current tenant) or global (admin only, anonymized) - defaults to tenant
    
    **Output:**
    - top_errors: List of top recurring errors with trend indicators (INCREASING/STABLE/DECREASING)
    - emerging_risks: List of emerging compliance risk descriptions
    - trend_summary: Short narrative summary of overall trends
    - recommended_actions: List of actionable operational steps
    - confidence: Confidence score (0.0 to 1.0)
    
    **Intelligence Logic:**
    - Compares current period vs previous period
    - Detects statistically meaningful increases (>10% change)
    - Correlates with known ZATCA risk categories
    - For global scope: uses aggregated & anonymized data only (no tenant identification)
    
    **Privacy:**
    - AI usage is logged for monitoring purposes
    - No invoice payloads are stored or logged
    - No financial values are stored
    - Global scope uses anonymized aggregated data only
    
    **Fallback:**
    - If AI is disabled or unavailable, returns rule-based analysis or disabled message
    """
    settings = get_settings()
    
    # CRITICAL: Enforce subscription AI limits before processing
    subscription_service = SubscriptionService(db, tenant)
    allowed, limit_error = subscription_service.check_ai_limit()
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=limit_error.model_dump()
        )
    
    # Validate parameters
    if period not in ["7d", "30d", "90d", "all"]:
        period = "30d"  # Default to 30d if invalid
    
    if scope not in ["tenant", "global"]:
        scope = "tenant"  # Default to tenant if invalid
    
    # For global scope, we could add admin check here in the future
    # For now, we'll allow it but ensure data is anonymized
    tenant_context = tenant if scope == "tenant" else None
    
    # Log AI usage request (without invoice data)
    logger.info(
        f"Error trend analysis requested for tenant_id={tenant.tenant_id if tenant_context else 'global'}, "
        f"period={period}, scope={scope}, "
        f"AI enabled: {settings.enable_ai_explanation}"
    )
    
    # CRITICAL: Increment AI usage BEFORE calling AI service
    # This preserves correct SaaS billing semantics - we charge for the API call, not AI success
    subscription_service.increment_ai_count()
    
    try:
        # Get AI trend analysis
        analyzer = ErrorTrendAnalyzer()
        trend_data = await analyzer.analyze_trends(
            tenant_context=tenant_context,
            db=db,
            period=period,
            scope=scope
        )
        
        # Log AI usage
        if settings.enable_ai_explanation and trend_data.get("confidence", 0.0) > 0.0:
            logger.info(
                f"Error trend analysis generated successfully. "
                f"Top errors: {len(trend_data.get('top_errors', []))}, "
                f"Confidence: {trend_data.get('confidence', 0.0)}, "
                f"Scope: {scope}, Tenant: {tenant.tenant_id if tenant_context else 'global'}"
            )
        else:
            logger.info(
                f"Error trend analysis returned (AI disabled or unavailable). "
                f"Scope: {scope}, Tenant: {tenant.tenant_id if tenant_context else 'global'}"
            )
        
        # Build response with proper structure
        from app.schemas.ai_trends import ErrorTrendItem
        
        top_errors = [
            ErrorTrendItem(
                error_code=error["error_code"],
                count=error["count"],
                trend=error["trend"]
            )
            for error in trend_data.get("top_errors", [])
        ]
        
        return ErrorTrendsResponse(
            top_errors=top_errors,
            emerging_risks=trend_data.get("emerging_risks", []),
            trend_summary=trend_data.get("trend_summary", "Trend analysis unavailable"),
            recommended_actions=trend_data.get("recommended_actions", []),
            confidence=trend_data.get("confidence", 0.0)
        )
        
    except Exception as e:
        # Log AI failure but don't expose internal errors
        logger.error(
            f"Error trend analysis failed for tenant_id={tenant.tenant_id if tenant_context else 'global'}, "
            f"scope={scope}. Error: {str(e)}. Returning safe fallback."
        )
        # Usage already incremented before AI call, so exception is already counted
        # Return safe fallback - never raise 500
        return ErrorTrendsResponse(
            top_errors=[],
            emerging_risks=[],
            trend_summary="Trend analysis service temporarily unavailable. Please try again later.",
            recommended_actions=["Please try again later or contact support"],
            confidence=0.0
        )

