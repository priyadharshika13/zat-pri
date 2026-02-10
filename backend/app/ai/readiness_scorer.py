"""
ZATCA Readiness Score AI Service.

Provides AI-powered tenant-level compliance health scoring.
Uses OpenRouter to synthesize aggregated metrics into an explainable readiness score.

CRITICAL: This service is ADVISORY-ONLY and READ-ONLY. AI never modifies invoice data,
XML structure, tax values, hashes, signatures, or any ZATCA-critical operations.
"""

import logging
from typing import Dict, Optional, List, Any
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import get_settings
from app.services.ai.openrouter_service import get_openrouter_service
from app.models.invoice_log import InvoiceLog, InvoiceLogStatus
from app.schemas.auth import TenantContext

logger = logging.getLogger(__name__)


class ReadinessScorer:
    """
    AI-powered ZATCA readiness scoring service.
    
    Uses OpenAI GPT-4o to synthesize:
    - Aggregated tenant invoice logs
    - Rejection frequency and trends
    - Error diversity and patterns
    - Historical risk signals
    
    Into a single, explainable compliance health score (0-100).
    
    CRITICAL: This service only generates scores. It does NOT modify
    any invoice data, XML, tax values, hashes, or signatures.
    """
    
    def __init__(
        self,
        model: Optional[str] = None
    ):
        """
        Initializes readiness scorer.
        
        Args:
            model: OpenRouter model name (uses default from config if not provided)
        """
        settings = get_settings()
        
        # CRITICAL: Check global AI toggle first
        if not settings.enable_ai_explanation:
            logger.info("AI readiness scoring is globally disabled (ENABLE_AI_EXPLANATION=false). AI will not be invoked.")
            self.openrouter = None
            self.ai_enabled = False
            return
        
        self.ai_enabled = True
        self.model = model or settings.openrouter_default_model
        
        # Get OpenRouter service
        try:
            self.openrouter = get_openrouter_service()
            if not self.openrouter.api_key:
                logger.warning("OpenRouter API key not configured. AI readiness scoring will not work.")
                self.openrouter = None
        except Exception as e:
            logger.warning(f"Failed to initialize OpenRouter service: {e}")
            self.openrouter = None
    
    async def compute_readiness_score(
        self,
        tenant_context: TenantContext,
        db: Session,
        period: str = "30d"
    ) -> Dict[str, Any]:
        """
        Computes tenant-level ZATCA readiness score.
        
        CRITICAL: This method only generates scores. It does NOT modify
        invoice data, XML, tax values, hashes, or signatures.
        
        Args:
            tenant_context: Tenant context for analysis
            db: Database session for querying aggregated metrics
            period: Analysis period ("30d", "90d", or "all")
        
        Returns:
            Dictionary containing:
                - readiness_score: int (0-100) or None if disabled
                - status: GREEN, AMBER, RED, or UNKNOWN
                - risk_factors: List of identified risk factors
                - improvement_suggestions: List of actionable improvement steps
                - confidence: Confidence score (0.0 to 1.0)
        """
        # CRITICAL: Check if AI is globally disabled
        if not self.ai_enabled:
            logger.info("AI readiness scoring skipped: AI is globally disabled (ENABLE_AI_EXPLANATION=false)")
            return self._get_disabled_response()
        
        if not self.openrouter:
            return self._get_disabled_response()
        
        # Aggregate tenant-level metrics
        metrics = self._aggregate_tenant_metrics(tenant_context, db, period)
        
        # Build prompt for AI
        prompt = self._build_scoring_prompt(metrics, period)
        
        try:
            # Call OpenRouter API
            response = await self.openrouter.call_openrouter(
                prompt=prompt,
                model=self.model,
                system_prompt=self._get_system_prompt(),
                temperature=0.2,  # Lower temperature for more consistent scoring
                max_tokens=1500,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            # Parse AI response
            ai_content = response["content"]
            
            # Log token usage (for monitoring, not stored in DB per requirements)
            usage = response.get("usage", {})
            logger.debug(
                f"OpenRouter token usage: prompt={usage.get('prompt_tokens', 0)}, "
                f"completion={usage.get('completion_tokens', 0)}, total={usage.get('total_tokens', 0)}"
            )
            
            return self._parse_ai_response(ai_content, metrics)
            
        except Exception as e:
            logger.error(f"Error calling OpenRouter API for readiness scoring: {e}")
            return self._fallback_scoring(metrics)
    
    def _aggregate_tenant_metrics(
        self,
        tenant_context: TenantContext,
        db: Session,
        period: str
    ) -> Dict[str, Any]:
        """
        Aggregates tenant-level metrics from invoice logs.
        
        Returns aggregated statistics without exposing invoice data.
        """
        try:
            # Determine date range
            if period == "30d":
                start_date = datetime.utcnow() - timedelta(days=30)
            elif period == "90d":
                start_date = datetime.utcnow() - timedelta(days=90)
            else:  # "all"
                start_date = datetime(2000, 1, 1)  # Very early date
            
            # Get all logs for this tenant in the period
            logs = db.query(InvoiceLog).filter(
                InvoiceLog.tenant_id == tenant_context.tenant_id,
                InvoiceLog.environment == tenant_context.environment,
                InvoiceLog.created_at >= start_date
            ).all()
            
            total_invoices = len(logs)
            
            # Count by status
            cleared_count = sum(1 for log in logs if log.status == InvoiceLogStatus.CLEARED)
            rejected_count = sum(1 for log in logs if log.status == InvoiceLogStatus.REJECTED)
            error_count = sum(1 for log in logs if log.status == InvoiceLogStatus.ERROR)
            submitted_count = sum(1 for log in logs if log.status == InvoiceLogStatus.SUBMITTED)
            
            # Calculate rejection rate
            rejection_rate = (rejected_count / total_invoices * 100) if total_invoices > 0 else 0.0
            success_rate = (cleared_count / total_invoices * 100) if total_invoices > 0 else 0.0
            
            # Get unique error codes
            error_codes = {}
            for log in logs:
                if log.zatca_response_code and log.status == InvoiceLogStatus.REJECTED:
                    code = log.zatca_response_code
                    error_codes[code] = error_codes.get(code, 0) + 1
            
            # Sort by frequency
            top_errors = sorted(error_codes.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Calculate error diversity (number of unique error codes)
            error_diversity = len(error_codes)
            
            # Check for recurring errors (same error code multiple times)
            recurring_errors = [code for code, count in error_codes.items() if count > 1]
            
            # Calculate trend (compare last half of period to first half)
            if total_invoices >= 4:  # Need enough data for trend
                midpoint = total_invoices // 2
                first_half = logs[:midpoint]
                second_half = logs[midpoint:]
                
                first_half_rejections = sum(1 for log in first_half if log.status == InvoiceLogStatus.REJECTED)
                second_half_rejections = sum(1 for log in second_half if log.status == InvoiceLogStatus.REJECTED)
                
                first_half_rate = (first_half_rejections / len(first_half) * 100) if first_half else 0.0
                second_half_rate = (second_half_rejections / len(second_half) * 100) if second_half else 0.0
                
                trend = "improving" if second_half_rate < first_half_rate else "worsening" if second_half_rate > first_half_rate else "stable"
                trend_delta = second_half_rate - first_half_rate
            else:
                trend = "insufficient_data"
                trend_delta = 0.0
            
            return {
                "total_invoices": total_invoices,
                "cleared_count": cleared_count,
                "rejected_count": rejected_count,
                "error_count": error_count,
                "submitted_count": submitted_count,
                "rejection_rate": round(rejection_rate, 2),
                "success_rate": round(success_rate, 2),
                "error_diversity": error_diversity,
                "top_errors": [{"code": code, "count": count} for code, count in top_errors],
                "recurring_errors": recurring_errors,
                "trend": trend,
                "trend_delta": round(trend_delta, 2),
                "period": period
            }
        except Exception as e:
            logger.warning(f"Error aggregating tenant metrics: {e}")
            return {
                "total_invoices": 0,
                "cleared_count": 0,
                "rejected_count": 0,
                "error_count": 0,
                "submitted_count": 0,
                "rejection_rate": 0.0,
                "success_rate": 0.0,
                "error_diversity": 0,
                "top_errors": [],
                "recurring_errors": [],
                "trend": "insufficient_data",
                "trend_delta": 0.0,
                "period": period
            }
    
    def _get_system_prompt(self) -> str:
        """
        Returns system prompt that enforces scoring-only behavior.
        
        CRITICAL: This prompt explicitly prohibits any data modification.
        """
        return """You are a ZATCA (Zakat, Tax and Customs Authority) compliance readiness scoring expert.

CRITICAL RULES - YOU MUST FOLLOW THESE STRICTLY:

1. SCORING ONLY: You ONLY generate readiness scores. You NEVER modify, calculate, or change:
   - Invoice values (quantities, prices, amounts)
   - Tax calculations or tax rates
   - XML structure or content
   - Hash values or digital signatures
   - UUIDs or invoice identifiers
   - Any ZATCA-critical data

2. YOUR ROLE: Synthesize aggregated tenant metrics into a compliance readiness score:
   - Score range: 0-100 (higher = more ready)
   - Status classification: GREEN (80-100), AMBER (50-79), RED (0-49)
   - Identify risk factors
   - Provide actionable improvement suggestions
   - Assess confidence in the score

3. DO NOT:
   - Generate or modify XML
   - Calculate tax amounts
   - Create hash values
   - Modify invoice data
   - Generate signatures
   - Block submissions

4. DO:
   - Consider rejection rate trends
   - Analyze error diversity and patterns
   - Identify recurring issues
   - Provide business-friendly insights
   - Make the score explainable

5. RESPONSE FORMAT: You MUST return valid JSON with this exact structure:
{
  "readiness_score": 0-100,
  "status": "GREEN" | "AMBER" | "RED",
  "risk_factors": ["factor1", "factor2", ...],
  "improvement_suggestions": ["suggestion1", "suggestion2", ...],
  "confidence": 0.0-1.0
}

6. SCORING GUIDELINES:
   - GREEN (80-100): Low rejection rate, few errors, improving trend
   - AMBER (50-79): Moderate rejection rate, some recurring errors, stable or mixed trend
   - RED (0-49): High rejection rate, many errors, worsening trend
   - Consider both current state and trends
   - Higher confidence when more data is available

Remember: You are a COMPLIANCE SCORING expert, not a data modification tool."""
    
    def _build_scoring_prompt(
        self,
        metrics: Dict[str, Any],
        period: str
    ) -> str:
        """Builds prompt for AI scoring."""
        prompt_parts = []
        
        prompt_parts.append("Analyze the following tenant-level ZATCA compliance metrics and compute a readiness score:")
        prompt_parts.append("")
        prompt_parts.append("ANALYSIS PERIOD: " + period)
        prompt_parts.append("")
        
        prompt_parts.append("AGGREGATED METRICS:")
        prompt_parts.append(f"- Total invoices: {metrics.get('total_invoices', 0)}")
        prompt_parts.append(f"- Cleared (successful): {metrics.get('cleared_count', 0)}")
        prompt_parts.append(f"- Rejected: {metrics.get('rejected_count', 0)}")
        prompt_parts.append(f"- Errors: {metrics.get('error_count', 0)}")
        prompt_parts.append(f"- Rejection rate: {metrics.get('rejection_rate', 0.0)}%")
        prompt_parts.append(f"- Success rate: {metrics.get('success_rate', 0.0)}%")
        prompt_parts.append("")
        
        if metrics.get('error_diversity', 0) > 0:
            prompt_parts.append("ERROR ANALYSIS:")
            prompt_parts.append(f"- Error diversity (unique error codes): {metrics.get('error_diversity', 0)}")
            
            top_errors = metrics.get('top_errors', [])
            if top_errors:
                prompt_parts.append("- Top error codes:")
                for error in top_errors:
                    prompt_parts.append(f"  - {error['code']}: {error['count']} occurrence(s)")
            
            recurring = metrics.get('recurring_errors', [])
            if recurring:
                prompt_parts.append(f"- Recurring errors (appeared multiple times): {', '.join(recurring)}")
            prompt_parts.append("")
        
        trend = metrics.get('trend', 'insufficient_data')
        if trend != 'insufficient_data':
            prompt_parts.append("TREND ANALYSIS:")
            prompt_parts.append(f"- Trend: {trend}")
            trend_delta = metrics.get('trend_delta', 0.0)
            if trend_delta != 0.0:
                prompt_parts.append(f"- Change: {abs(trend_delta):.2f}% {'improvement' if trend == 'improving' else 'deterioration'}")
            prompt_parts.append("")
        
        if metrics.get('total_invoices', 0) == 0:
            prompt_parts.append("⚠️ No invoice data available for this period.")
            prompt_parts.append("")
        
        prompt_parts.append("SCORING REQUIREMENTS:")
        prompt_parts.append("1. Compute readiness_score (0-100):")
        prompt_parts.append("   - Consider rejection rate (lower is better)")
        prompt_parts.append("   - Consider error diversity (lower is better)")
        prompt_parts.append("   - Consider recurring errors (fewer is better)")
        prompt_parts.append("   - Consider trend (improving is better)")
        prompt_parts.append("   - Consider success rate (higher is better)")
        prompt_parts.append("2. Classify status:")
        prompt_parts.append("   - GREEN (80-100): Excellent compliance")
        prompt_parts.append("   - AMBER (50-79): Moderate compliance, needs attention")
        prompt_parts.append("   - RED (0-49): Poor compliance, urgent action needed")
        prompt_parts.append("3. Identify risk_factors (specific issues affecting readiness)")
        prompt_parts.append("4. Provide improvement_suggestions (actionable steps to improve score)")
        prompt_parts.append("5. Assess confidence (0.0-1.0) based on data availability and quality")
        prompt_parts.append("")
        
        prompt_parts.append("Please provide a JSON response with readiness_score, status, risk_factors, improvement_suggestions, and confidence.")
        prompt_parts.append("")
        prompt_parts.append("IMPORTANT: Only provide scoring and analysis. Do NOT generate or modify any invoice data, XML, tax values, hashes, or signatures.")
        
        return "\n".join(prompt_parts)
    
    def _parse_ai_response(
        self,
        ai_content: str,
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parses AI response into structured format.
        
        Validates and ensures all required fields are present.
        """
        try:
            # Parse JSON response
            parsed = json.loads(ai_content)
            
            readiness_score = parsed.get("readiness_score")
            if readiness_score is not None:
                readiness_score = int(readiness_score)
                readiness_score = max(0, min(100, readiness_score))  # Clamp to [0, 100]
            else:
                readiness_score = None
            
            status = parsed.get("status", "UNKNOWN").upper()
            if status not in ["GREEN", "AMBER", "RED", "UNKNOWN"]:
                # Auto-classify based on score if status is invalid
                if readiness_score is not None:
                    if readiness_score >= 80:
                        status = "GREEN"
                    elif readiness_score >= 50:
                        status = "AMBER"
                    else:
                        status = "RED"
                else:
                    status = "UNKNOWN"
            
            risk_factors = parsed.get("risk_factors", [])
            if not isinstance(risk_factors, list):
                risk_factors = []
            
            improvement_suggestions = parsed.get("improvement_suggestions", [])
            if not isinstance(improvement_suggestions, list):
                improvement_suggestions = []
            
            confidence = float(parsed.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0.0, 1.0]
            
            # Adjust confidence based on data availability
            if metrics.get('total_invoices', 0) < 5:
                confidence = min(confidence, 0.6)  # Lower confidence with limited data
            
            return {
                "readiness_score": readiness_score,
                "status": status,
                "risk_factors": risk_factors,
                "improvement_suggestions": improvement_suggestions,
                "confidence": confidence
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._fallback_scoring(metrics)
    
    def _fallback_scoring(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provides fallback scoring when AI is unavailable.
        
        Uses rule-based heuristics to compute basic score.
        """
        total_invoices = metrics.get('total_invoices', 0)
        
        if total_invoices == 0:
            return {
                "readiness_score": None,
                "status": "UNKNOWN",
                "risk_factors": ["No invoice data available for analysis"],
                "improvement_suggestions": ["Submit invoices to generate readiness score"],
                "confidence": 0.0
            }
        
        rejection_rate = metrics.get('rejection_rate', 0.0)
        error_diversity = metrics.get('error_diversity', 0)
        recurring_errors = len(metrics.get('recurring_errors', []))
        
        # Rule-based scoring
        # Start with 100, deduct points for issues
        score = 100
        
        # Deduct for rejection rate
        if rejection_rate > 50:
            score -= 40
        elif rejection_rate > 30:
            score -= 25
        elif rejection_rate > 15:
            score -= 15
        elif rejection_rate > 5:
            score -= 10
        elif rejection_rate > 0:
            score -= 5
        
        # Deduct for error diversity
        score -= min(error_diversity * 3, 20)
        
        # Deduct for recurring errors
        score -= min(recurring_errors * 5, 15)
        
        # Consider trend
        trend = metrics.get('trend', 'insufficient_data')
        if trend == 'worsening':
            score -= 10
        elif trend == 'improving':
            score += 5
        
        score = max(0, min(100, score))  # Clamp to [0, 100]
        
        # Classify status
        if score >= 80:
            status = "GREEN"
        elif score >= 50:
            status = "AMBER"
        else:
            status = "RED"
        
        # Generate risk factors
        risk_factors = []
        if rejection_rate > 15:
            risk_factors.append(f"High rejection rate ({rejection_rate:.1f}%)")
        if error_diversity > 3:
            risk_factors.append(f"High error diversity ({error_diversity} unique error codes)")
        if recurring_errors:
            risk_factors.append(f"Recurring errors detected ({len(recurring_errors)} error types)")
        if trend == 'worsening':
            risk_factors.append("Rejection rate is worsening over time")
        
        # Generate improvement suggestions
        improvement_suggestions = []
        if rejection_rate > 0:
            improvement_suggestions.append("Review and fix common rejection causes")
        if recurring_errors:
            improvement_suggestions.append("Address recurring error patterns")
        if error_diversity > 2:
            improvement_suggestions.append("Standardize invoice generation process")
        improvement_suggestions.append("Use Smart Pre-Check Advisor before submission")
        
        return {
            "readiness_score": score,
            "status": status,
            "risk_factors": risk_factors,
            "improvement_suggestions": improvement_suggestions,
            "confidence": 0.5  # Lower confidence without AI
        }
    
    def _get_disabled_response(self) -> Dict[str, Any]:
        """
        Returns response when AI is disabled.
        """
        return {
            "readiness_score": None,
            "status": "UNKNOWN",
            "risk_factors": [],
            "improvement_suggestions": [],
            "confidence": 0.0
        }

