"""
Root Cause Intelligence AI Service.

Provides AI-powered root cause analysis of ZATCA invoice failures.
Uses OpenRouter to identify WHY an invoice failed, not just WHAT failed.

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


class RootCauseEngine:
    """
    AI-powered root cause analysis service for ZATCA failures.
    
    Uses OpenAI GPT-4o to analyze:
    - WHY an invoice failed (not just what failed)
    - Primary root cause
    - Secondary contributing factors
    - Prevention strategies
    
    CRITICAL: This service only generates analysis. It does NOT modify
    any invoice data, XML, tax values, hashes, or signatures.
    """
    
    def __init__(
        self,
        model: Optional[str] = None
    ):
        """
        Initializes root cause engine.
        
        Args:
            model: OpenRouter model name (uses default from config if not provided)
        """
        settings = get_settings()
        
        # CRITICAL: Check global AI toggle first
        if not settings.enable_ai_explanation:
            logger.info("AI root cause analysis is globally disabled (ENABLE_AI_EXPLANATION=false). AI will not be invoked.")
            self.openrouter = None
            self.ai_enabled = False
            return
        
        self.ai_enabled = True
        self.model = model or settings.openrouter_default_model
        
        # Get OpenRouter service
        try:
            self.openrouter = get_openrouter_service()
            if not self.openrouter.api_key:
                logger.warning("OpenRouter API key not configured. AI root cause analysis will not work.")
                self.openrouter = None
        except Exception as e:
            logger.warning(f"Failed to initialize OpenRouter service: {e}")
            self.openrouter = None
    
    async def analyze_root_cause(
        self,
        error_code: str,
        error_message: Optional[str],
        rule_based_explanation: Optional[Dict[str, Any]],
        tenant_context: TenantContext,
        db: Session,
        environment: str
    ) -> Dict[str, Any]:
        """
        Analyzes root cause of ZATCA failure.
        
        CRITICAL: This method only generates analysis. It does NOT modify
        invoice data, XML, tax values, hashes, or signatures.
        
        Args:
            error_code: ZATCA error code (e.g., "ZATCA-2001")
            error_message: Error message from ZATCA (optional)
            rule_based_explanation: Rule-based explanation from error catalog (optional)
            tenant_context: Tenant context for historical analysis
            db: Database session for querying historical patterns
            environment: Target environment (SANDBOX or PRODUCTION)
        
        Returns:
            Dictionary containing:
                - primary_cause: Single dominant root cause
                - secondary_causes: List of supporting contributing factors
                - prevention_checklist: List of actionable prevention steps
                - confidence: Confidence score (0.0 to 1.0)
        """
        # CRITICAL: Check if AI is globally disabled
        if not self.ai_enabled:
            logger.info("AI root cause analysis skipped: AI is globally disabled (ENABLE_AI_EXPLANATION=false)")
            return self._get_disabled_response()
        
        if not self.openrouter:
            return self._get_disabled_response()
        
        # Get historical rejection patterns for this tenant
        historical_context = self._get_historical_context(
            error_code,
            tenant_context,
            db,
            environment
        )
        
        # Build prompt for AI
        prompt = self._build_analysis_prompt(
            error_code,
            error_message,
            rule_based_explanation,
            historical_context,
            environment
        )
        
        try:
            # Call OpenRouter API
            response = await self.openrouter.call_openrouter(
                prompt=prompt,
                model=self.model,
                system_prompt=self._get_system_prompt(),
                temperature=0.2,  # Lower temperature for more consistent, factual analysis
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
            
            return self._parse_ai_response(ai_content)
            
        except Exception as e:
            logger.error(f"Error calling OpenRouter API for root cause analysis: {e}")
            return self._fallback_analysis(error_code, rule_based_explanation)
    
    def _get_historical_context(
        self,
        error_code: str,
        tenant_context: TenantContext,
        db: Session,
        environment: str
    ) -> Dict[str, Any]:
        """
        Gets historical rejection patterns for this specific error code and tenant.
        
        Returns aggregated statistics without exposing invoice data.
        """
        try:
            # Get rejection frequency for this specific error code (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            # Count rejections with this error code
            error_rejections = db.query(func.count(InvoiceLog.id)).filter(
                InvoiceLog.tenant_id == tenant_context.tenant_id,
                InvoiceLog.environment == environment,
                InvoiceLog.status == InvoiceLogStatus.REJECTED,
                InvoiceLog.zatca_response_code == error_code,
                InvoiceLog.created_at >= thirty_days_ago
            ).scalar() or 0
            
            # Total rejections for this tenant (any error code)
            total_rejections = db.query(func.count(InvoiceLog.id)).filter(
                InvoiceLog.tenant_id == tenant_context.tenant_id,
                InvoiceLog.environment == environment,
                InvoiceLog.status == InvoiceLogStatus.REJECTED,
                InvoiceLog.created_at >= thirty_days_ago
            ).scalar() or 0
            
            # Most common error codes for this tenant (top 5)
            common_errors = db.query(
                InvoiceLog.zatca_response_code,
                func.count(InvoiceLog.id).label('count')
            ).filter(
                InvoiceLog.tenant_id == tenant_context.tenant_id,
                InvoiceLog.environment == environment,
                InvoiceLog.status == InvoiceLogStatus.REJECTED,
                InvoiceLog.zatca_response_code.isnot(None),
                InvoiceLog.created_at >= thirty_days_ago
            ).group_by(InvoiceLog.zatca_response_code).order_by(
                func.count(InvoiceLog.id).desc()
            ).limit(5).all()
            
            error_frequency = (error_rejections / total_rejections * 100) if total_rejections > 0 else 0.0
            
            return {
                "error_code": error_code,
                "error_rejections_30d": error_rejections,
                "total_rejections_30d": total_rejections,
                "error_frequency_percent": round(error_frequency, 2),
                "common_error_codes": [code for code, _ in common_errors] if common_errors else [],
                "is_recurring": error_rejections > 1
            }
        except Exception as e:
            logger.warning(f"Error fetching historical context: {e}")
            return {
                "error_code": error_code,
                "error_rejections_30d": 0,
                "total_rejections_30d": 0,
                "error_frequency_percent": 0.0,
                "common_error_codes": [],
                "is_recurring": False
            }
    
    def _get_system_prompt(self) -> str:
        """
        Returns system prompt that enforces analysis-only behavior.
        
        CRITICAL: This prompt explicitly prohibits any data modification.
        """
        return """You are a ZATCA (Zakat, Tax and Customs Authority) root cause analysis expert.

CRITICAL RULES - YOU MUST FOLLOW THESE STRICTLY:

1. ANALYSIS ONLY: You ONLY generate root cause analysis. You NEVER modify, calculate, or change:
   - Invoice values (quantities, prices, amounts)
   - Tax calculations or tax rates
   - XML structure or content
   - Hash values or digital signatures
   - UUIDs or invoice identifiers
   - Any ZATCA-critical data

2. YOUR ROLE: Analyze WHY an invoice failed, not just WHAT failed:
   - Identify the PRIMARY root cause (single dominant reason)
   - Identify SECONDARY contributing factors (supporting reasons)
   - Provide actionable PREVENTION checklist (steps to prevent recurrence)
   - Assess confidence in your analysis

3. DO NOT:
   - Generate or modify XML
   - Calculate tax amounts
   - Create hash values
   - Modify invoice data
   - Generate signatures
   - Re-submit invoices

4. DO:
   - Think deeply about systemic issues, not just symptoms
   - Consider business process problems, not just technical errors
   - Provide actionable, specific prevention steps
   - Consider historical patterns and recurring issues
   - Focus on WHY the error occurred, not just what the error is

5. RESPONSE FORMAT: You MUST return valid JSON with this exact structure:
{
  "primary_cause": "Single dominant root cause explanation",
  "secondary_causes": ["Supporting factor 1", "Supporting factor 2", ...],
  "prevention_checklist": ["Actionable step 1", "Actionable step 2", ...],
  "confidence": 0.0-1.0
}

6. ANALYSIS DEPTH:
   - Primary cause should explain the SYSTEMIC reason, not just the symptom
   - Secondary causes should identify contributing factors
   - Prevention checklist should be specific, actionable, and address root causes
   - Confidence should reflect how certain you are based on available information

Remember: You are a ROOT CAUSE ANALYSIS expert, not a data modification tool."""
    
    def _build_analysis_prompt(
        self,
        error_code: str,
        error_message: Optional[str],
        rule_based_explanation: Optional[Dict[str, Any]],
        historical_context: Dict[str, Any],
        environment: str
    ) -> str:
        """Builds prompt for AI root cause analysis."""
        prompt_parts = []
        
        prompt_parts.append("Analyze the root cause of the following ZATCA failure:")
        prompt_parts.append("")
        prompt_parts.append(f"ERROR CODE: {error_code}")
        prompt_parts.append("")
        
        if error_message:
            prompt_parts.append(f"ERROR MESSAGE: {error_message}")
            prompt_parts.append("")
        
        if rule_based_explanation:
            prompt_parts.append("RULE-BASED EXPLANATION (from error catalog):")
            if rule_based_explanation.get("title"):
                prompt_parts.append(f"  Title: {rule_based_explanation['title']}")
            if rule_based_explanation.get("technical_reason"):
                prompt_parts.append(f"  Technical Reason: {rule_based_explanation['technical_reason']}")
            if rule_based_explanation.get("fix_suggestion"):
                prompt_parts.append(f"  Fix Suggestion: {rule_based_explanation['fix_suggestion']}")
            prompt_parts.append("")
            prompt_parts.append("Use this as context, but go deeper to identify the ROOT CAUSE, not just the symptom.")
            prompt_parts.append("")
        
        prompt_parts.append("HISTORICAL CONTEXT (tenant rejection patterns):")
        prompt_parts.append(f"- This error occurred {historical_context.get('error_rejections_30d', 0)} time(s) in the last 30 days")
        prompt_parts.append(f"- Total rejections for this tenant: {historical_context.get('total_rejections_30d', 0)}")
        if historical_context.get('error_frequency_percent', 0) > 0:
            prompt_parts.append(f"- This error represents {historical_context.get('error_frequency_percent', 0)}% of all rejections")
        if historical_context.get('is_recurring'):
            prompt_parts.append("- ⚠️ This is a RECURRING error - indicates a systemic issue, not a one-time mistake")
        if historical_context.get('common_error_codes'):
            prompt_parts.append(f"- Most common errors for this tenant: {', '.join(historical_context['common_error_codes'])}")
        prompt_parts.append("")
        
        prompt_parts.append("TARGET ENVIRONMENT: " + environment)
        prompt_parts.append("")
        
        prompt_parts.append("ANALYSIS REQUIREMENTS:")
        prompt_parts.append("1. PRIMARY CAUSE: Identify the single dominant root cause (WHY this happened, not just what happened)")
        prompt_parts.append("   - Think about business processes, data entry practices, calculation methods")
        prompt_parts.append("   - Consider systemic issues, not just technical errors")
        prompt_parts.append("2. SECONDARY CAUSES: List supporting contributing factors")
        prompt_parts.append("3. PREVENTION CHECKLIST: Provide specific, actionable steps to prevent recurrence")
        prompt_parts.append("   - Focus on fixing the root cause, not just the symptom")
        prompt_parts.append("   - Include process improvements, validation steps, automation suggestions")
        prompt_parts.append("4. CONFIDENCE: Assess how certain you are (0.0 to 1.0) based on available information")
        prompt_parts.append("")
        
        prompt_parts.append("COMMON ZATCA ROOT CAUSES TO CONSIDER:")
        prompt_parts.append("- Manual data entry errors")
        prompt_parts.append("- Inconsistent calculation logic across systems")
        prompt_parts.append("- Missing validation in invoice generation workflow")
        prompt_parts.append("- Rounding differences between line items and totals")
        prompt_parts.append("- Tax rate configuration errors")
        prompt_parts.append("- Business process gaps (missing approvals, reviews)")
        prompt_parts.append("- Integration issues between systems")
        prompt_parts.append("- Lack of automated validation before submission")
        prompt_parts.append("")
        
        prompt_parts.append("Please provide a JSON response with primary_cause, secondary_causes, prevention_checklist, and confidence.")
        prompt_parts.append("")
        prompt_parts.append("IMPORTANT: Only provide analysis. Do NOT generate or modify any invoice data, XML, tax values, hashes, or signatures.")
        
        return "\n".join(prompt_parts)
    
    def _parse_ai_response(self, ai_content: str) -> Dict[str, Any]:
        """
        Parses AI response into structured format.
        
        Validates and ensures all required fields are present.
        """
        try:
            # Parse JSON response
            parsed = json.loads(ai_content)
            
            primary_cause = parsed.get("primary_cause", "")
            if not primary_cause:
                primary_cause = "Root cause analysis unavailable"
            
            secondary_causes = parsed.get("secondary_causes", [])
            if not isinstance(secondary_causes, list):
                secondary_causes = []
            
            prevention_checklist = parsed.get("prevention_checklist", [])
            if not isinstance(prevention_checklist, list):
                prevention_checklist = []
            
            confidence = float(parsed.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0.0, 1.0]
            
            return {
                "primary_cause": primary_cause,
                "secondary_causes": secondary_causes,
                "prevention_checklist": prevention_checklist,
                "confidence": confidence
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._fallback_analysis(None, None)
    
    def _fallback_analysis(
        self,
        error_code: Optional[str],
        rule_based_explanation: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Provides fallback analysis when AI is unavailable.
        
        Uses rule-based explanation to provide basic root cause analysis.
        """
        if rule_based_explanation:
            primary_cause = rule_based_explanation.get(
                "technical_reason",
                rule_based_explanation.get("title", "Root cause analysis unavailable")
            )
            prevention_checklist = []
            if rule_based_explanation.get("fix_suggestion"):
                prevention_checklist.append(rule_based_explanation["fix_suggestion"])
            prevention_checklist.append("Review invoice data before submission")
            prevention_checklist.append("Implement automated validation checks")
        else:
            primary_cause = "Root cause analysis unavailable. AI service temporarily unavailable."
            prevention_checklist = [
                "Review the error code and message",
                "Consult ZATCA documentation",
                "Verify invoice data manually"
            ]
        
        return {
            "primary_cause": primary_cause,
            "secondary_causes": [],
            "prevention_checklist": prevention_checklist,
            "confidence": 0.3  # Lower confidence without AI
        }
    
    def _get_disabled_response(self) -> Dict[str, Any]:
        """
        Returns response when AI is disabled.
        """
        return {
            "primary_cause": "AI root cause analysis disabled",
            "secondary_causes": [],
            "prevention_checklist": [],
            "confidence": 0.0
        }

