"""
Error & Trend Intelligence AI Service.

Provides AI-powered time-based trend analysis of ZATCA errors and risks.
Uses OpenRouter to identify patterns, emerging risks, and operational recommendations.

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


class ErrorTrendAnalyzer:
    """
    AI-powered error trend analysis service.
    
    Uses OpenAI GPT-4o to analyze:
    - Historical error patterns over time
    - Increasing vs decreasing trends
    - Emerging compliance risks
    - Operational recommendations
    
    CRITICAL: This service only generates insights. It does NOT modify
    any invoice data, XML, tax values, hashes, or signatures.
    """
    
    def __init__(
        self,
        model: Optional[str] = None
    ):
        """
        Initializes error trend analyzer.
        
        Args:
            model: OpenRouter model name (uses default from config if not provided)
        """
        settings = get_settings()
        
        # CRITICAL: Check global AI toggle first
        if not settings.enable_ai_explanation:
            logger.info("AI trend analysis is globally disabled (ENABLE_AI_EXPLANATION=false). AI will not be invoked.")
            self.openrouter = None
            self.ai_enabled = False
            return
        
        self.ai_enabled = True
        self.model = model or settings.openrouter_default_model
        
        # Get OpenRouter service
        try:
            self.openrouter = get_openrouter_service()
            if not self.openrouter.api_key:
                logger.warning("OpenRouter API key not configured. AI trend analysis will not work.")
                self.openrouter = None
        except Exception as e:
            logger.warning(f"Failed to initialize OpenRouter service: {e}")
            self.openrouter = None
    
    async def analyze_trends(
        self,
        tenant_context: Optional[TenantContext],
        db: Session,
        period: str = "30d",
        scope: str = "tenant"
    ) -> Dict[str, Any]:
        """
        Analyzes error trends over time.
        
        CRITICAL: This method only generates insights. It does NOT modify
        invoice data, XML, tax values, hashes, or signatures.
        
        Args:
            tenant_context: Tenant context (None for global scope)
            db: Database session for querying aggregated metrics
            period: Analysis period ("7d", "30d", "90d", or "all")
            scope: Analysis scope ("tenant" or "global")
        
        Returns:
            Dictionary containing:
                - top_errors: List of error trends
                - emerging_risks: List of emerging risk descriptions
                - trend_summary: Narrative summary
                - recommended_actions: List of actionable steps
                - confidence: Confidence score (0.0 to 1.0)
        """
        # CRITICAL: Check if AI is globally disabled
        if not self.ai_enabled:
            logger.info("AI trend analysis skipped: AI is globally disabled (ENABLE_AI_EXPLANATION=false)")
            return self._get_disabled_response()
        
        if not self.openrouter:
            return self._get_disabled_response()
        
        # Aggregate error statistics
        error_stats = self._aggregate_error_statistics(tenant_context, db, period, scope)
        
        # Build prompt for AI
        prompt = self._build_analysis_prompt(error_stats, period, scope)
        
        try:
            # Call OpenRouter API
            response = await self.openrouter.call_openrouter(
                prompt=prompt,
                model=self.model,
                system_prompt=self._get_system_prompt(),
                temperature=0.2,  # Lower temperature for more consistent analysis
                max_tokens=2000,
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
            
            return self._parse_ai_response(ai_content, error_stats)
            
        except Exception as e:
            logger.error(f"Error calling OpenRouter API for trend analysis: {e}")
            return self._fallback_analysis(error_stats)
    
    def _aggregate_error_statistics(
        self,
        tenant_context: Optional[TenantContext],
        db: Session,
        period: str,
        scope: str
    ) -> Dict[str, Any]:
        """
        Aggregates error statistics for trend analysis.
        
        Returns aggregated statistics without exposing invoice data.
        """
        try:
            # Determine date ranges
            if period == "7d":
                current_start = datetime.utcnow() - timedelta(days=7)
                previous_start = datetime.utcnow() - timedelta(days=14)
                previous_end = datetime.utcnow() - timedelta(days=7)
            elif period == "30d":
                current_start = datetime.utcnow() - timedelta(days=30)
                previous_start = datetime.utcnow() - timedelta(days=60)
                previous_end = datetime.utcnow() - timedelta(days=30)
            elif period == "90d":
                current_start = datetime.utcnow() - timedelta(days=90)
                previous_start = datetime.utcnow() - timedelta(days=180)
                previous_end = datetime.utcnow() - timedelta(days=90)
            else:  # "all"
                current_start = datetime(2000, 1, 1)
                previous_start = datetime(2000, 1, 1)
                previous_end = datetime.utcnow() - timedelta(days=365)
            
            # Build base query
            base_query = db.query(InvoiceLog).filter(
                InvoiceLog.status == InvoiceLogStatus.REJECTED,
                InvoiceLog.zatca_response_code.isnot(None)
            )
            
            # Apply tenant filter if scope is tenant
            if scope == "tenant" and tenant_context:
                base_query = base_query.filter(
                    InvoiceLog.tenant_id == tenant_context.tenant_id,
                    InvoiceLog.environment == tenant_context.environment
                )
            
            # Current period errors
            current_errors = base_query.filter(
                InvoiceLog.created_at >= current_start
            ).all()
            
            # Previous period errors (for trend comparison)
            previous_errors = base_query.filter(
                InvoiceLog.created_at >= previous_start,
                InvoiceLog.created_at < previous_end
            ).all() if period != "all" else []
            
            # Count errors by code for current period
            current_error_counts = {}
            for log in current_errors:
                code = log.zatca_response_code
                current_error_counts[code] = current_error_counts.get(code, 0) + 1
            
            # Count errors by code for previous period
            previous_error_counts = {}
            for log in previous_errors:
                code = log.zatca_response_code
                previous_error_counts[code] = previous_error_counts.get(code, 0) + 1
            
            # Calculate trends
            top_errors = []
            for code, current_count in sorted(current_error_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                previous_count = previous_error_counts.get(code, 0)
                
                # Determine trend
                if previous_count == 0:
                    if current_count > 0:
                        trend = "INCREASING"  # New error
                    else:
                        trend = "STABLE"
                else:
                    change_percent = ((current_count - previous_count) / previous_count) * 100
                    if change_percent > 10:  # More than 10% increase
                        trend = "INCREASING"
                    elif change_percent < -10:  # More than 10% decrease
                        trend = "DECREASING"
                    else:
                        trend = "STABLE"
                
                top_errors.append({
                    "error_code": code,
                    "count": current_count,
                    "previous_count": previous_count,
                    "trend": trend,
                    "change_percent": round(change_percent if previous_count > 0 else 0, 2)
                })
            
            # Calculate overall statistics
            total_current = len(current_errors)
            total_previous = len(previous_errors)
            
            overall_trend = "STABLE"
            if total_previous > 0:
                overall_change = ((total_current - total_previous) / total_previous) * 100
                if overall_change > 10:
                    overall_trend = "INCREASING"
                elif overall_change < -10:
                    overall_trend = "DECREASING"
            elif total_current > 0:
                overall_trend = "INCREASING"
            
            # Get unique error codes
            unique_errors = len(current_error_counts)
            
            return {
                "period": period,
                "scope": scope,
                "total_current_errors": total_current,
                "total_previous_errors": total_previous,
                "overall_trend": overall_trend,
                "unique_error_codes": unique_errors,
                "top_errors": top_errors,
                "has_comparison_data": len(previous_errors) > 0
            }
        except Exception as e:
            logger.warning(f"Error aggregating error statistics: {e}")
            return {
                "period": period,
                "scope": scope,
                "total_current_errors": 0,
                "total_previous_errors": 0,
                "overall_trend": "STABLE",
                "unique_error_codes": 0,
                "top_errors": [],
                "has_comparison_data": False
            }
    
    def _get_system_prompt(self) -> str:
        """
        Returns system prompt that enforces analysis-only behavior.
        
        CRITICAL: This prompt explicitly prohibits any data modification.
        """
        return """You are a ZATCA (Zakat, Tax and Customs Authority) error trend analysis expert.

CRITICAL RULES - YOU MUST FOLLOW THESE STRICTLY:

1. ANALYSIS ONLY: You ONLY generate trend insights. You NEVER modify, calculate, or change:
   - Invoice values (quantities, prices, amounts)
   - Tax calculations or tax rates
   - XML structure or content
   - Hash values or digital signatures
   - UUIDs or invoice identifiers
   - Any ZATCA-critical data

2. YOUR ROLE: Analyze error trends and provide operational intelligence:
   - Identify top recurring errors with trend indicators
   - Detect emerging compliance risks
   - Provide narrative trend summary
   - Recommend actionable operational steps

3. DO NOT:
   - Generate or modify XML
   - Calculate tax amounts
   - Create hash values
   - Modify invoice data
   - Generate signatures
   - Trigger submissions

4. DO:
   - Compare current period vs previous period
   - Detect statistically meaningful increases
   - Correlate with known ZATCA risk categories
   - Provide specific, actionable recommendations
   - Focus on operational and strategic insights

5. RESPONSE FORMAT: You MUST return valid JSON with this exact structure:
{
  "top_errors": [
    {"error_code": "ZATCA-2001", "count": 34, "trend": "INCREASING"},
    {"error_code": "ZATCA-3001", "count": 12, "trend": "DECREASING"}
  ],
  "emerging_risks": ["risk1", "risk2", ...],
  "trend_summary": "Narrative summary of overall trends",
  "recommended_actions": ["action1", "action2", ...],
  "confidence": 0.0-1.0
}

6. TREND CLASSIFICATION:
   - INCREASING: Error count increased significantly (>10%) or new error appeared
   - DECREASING: Error count decreased significantly (>10%)
   - STABLE: Error count remained relatively stable (±10%)

7. EMERGING RISKS:
   - Focus on patterns, not individual errors
   - Identify systemic issues
   - Consider compliance implications

Remember: You are a TREND ANALYSIS expert, not a data modification tool."""
    
    def _build_analysis_prompt(
        self,
        error_stats: Dict[str, Any],
        period: str,
        scope: str
    ) -> str:
        """Builds prompt for AI trend analysis."""
        prompt_parts = []
        
        prompt_parts.append("Analyze the following ZATCA error trends and provide operational intelligence:")
        prompt_parts.append("")
        prompt_parts.append(f"ANALYSIS PERIOD: {period}")
        prompt_parts.append(f"SCOPE: {scope}")
        prompt_parts.append("")
        
        prompt_parts.append("ERROR STATISTICS:")
        prompt_parts.append(f"- Total errors (current period): {error_stats.get('total_current_errors', 0)}")
        if error_stats.get('has_comparison_data'):
            prompt_parts.append(f"- Total errors (previous period): {error_stats.get('total_previous_errors', 0)}")
            prompt_parts.append(f"- Overall trend: {error_stats.get('overall_trend', 'STABLE')}")
        prompt_parts.append(f"- Unique error codes: {error_stats.get('unique_error_codes', 0)}")
        prompt_parts.append("")
        
        top_errors = error_stats.get('top_errors', [])
        if top_errors:
            prompt_parts.append("TOP ERRORS (with trend indicators):")
            for error in top_errors:
                trend_desc = error.get('trend', 'STABLE')
                change_info = ""
                if error.get('previous_count', 0) > 0:
                    change_info = f" (was {error['previous_count']}, change: {error.get('change_percent', 0):.1f}%)"
                prompt_parts.append(f"  - {error['error_code']}: {error['count']} occurrences, trend: {trend_desc}{change_info}")
            prompt_parts.append("")
        else:
            prompt_parts.append("No errors found in the analysis period.")
            prompt_parts.append("")
        
        prompt_parts.append("ANALYSIS REQUIREMENTS:")
        prompt_parts.append("1. TOP ERRORS: List top errors with error_code, count, and trend (INCREASING/STABLE/DECREASING)")
        prompt_parts.append("2. EMERGING RISKS: Identify patterns and systemic issues that are becoming more common")
        prompt_parts.append("3. TREND SUMMARY: Provide a short narrative (2-3 sentences) summarizing overall trends")
        prompt_parts.append("4. RECOMMENDED ACTIONS: Provide specific, actionable operational steps based on the trends")
        prompt_parts.append("5. CONFIDENCE: Assess how certain you are (0.0 to 1.0) based on data availability")
        prompt_parts.append("")
        
        prompt_parts.append("COMMON ZATCA RISK CATEGORIES TO CONSIDER:")
        prompt_parts.append("- VAT calculation and rounding issues")
        prompt_parts.append("- Missing or invalid VAT numbers")
        prompt_parts.append("- Tax category mismatches")
        prompt_parts.append("- Document total inconsistencies")
        prompt_parts.append("- Date and time format issues")
        prompt_parts.append("- Line item calculation errors")
        prompt_parts.append("")
        
        prompt_parts.append("Please provide a JSON response with top_errors, emerging_risks, trend_summary, recommended_actions, and confidence.")
        prompt_parts.append("")
        prompt_parts.append("IMPORTANT: Only provide analysis and insights. Do NOT generate or modify any invoice data, XML, tax values, hashes, or signatures.")
        
        return "\n".join(prompt_parts)
    
    def _parse_ai_response(
        self,
        ai_content: str,
        error_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parses AI response into structured format.
        
        Validates and ensures all required fields are present.
        """
        try:
            # Parse JSON response
            parsed = json.loads(ai_content)
            
            # Parse top_errors
            top_errors_raw = parsed.get("top_errors", [])
            top_errors = []
            for error in top_errors_raw:
                if isinstance(error, dict):
                    error_code = error.get("error_code", "")
                    count = int(error.get("count", 0))
                    trend = error.get("trend", "STABLE").upper()
                    if trend not in ["INCREASING", "STABLE", "DECREASING"]:
                        trend = "STABLE"
                    if error_code:
                        top_errors.append({
                            "error_code": error_code,
                            "count": count,
                            "trend": trend
                        })
            
            # If AI didn't provide top_errors, use from error_stats
            if not top_errors and error_stats.get('top_errors'):
                for error in error_stats['top_errors'][:5]:
                    top_errors.append({
                        "error_code": error['error_code'],
                        "count": error['count'],
                        "trend": error['trend']
                    })
            
            emerging_risks = parsed.get("emerging_risks", [])
            if not isinstance(emerging_risks, list):
                emerging_risks = []
            
            trend_summary = parsed.get("trend_summary", "")
            if not trend_summary:
                # Generate basic summary from stats
                overall_trend = error_stats.get('overall_trend', 'STABLE')
                total_errors = error_stats.get('total_current_errors', 0)
                if total_errors == 0:
                    trend_summary = "No errors detected in the analysis period."
                else:
                    trend_summary = f"Overall rejection trend is {overall_trend.lower()}. {total_errors} total errors detected."
            
            recommended_actions = parsed.get("recommended_actions", [])
            if not isinstance(recommended_actions, list):
                recommended_actions = []
            
            confidence = float(parsed.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0.0, 1.0]
            
            # Adjust confidence based on data availability
            if error_stats.get('total_current_errors', 0) < 5:
                confidence = min(confidence, 0.6)  # Lower confidence with limited data
            if not error_stats.get('has_comparison_data'):
                confidence = min(confidence, 0.7)  # Lower confidence without comparison data
            
            return {
                "top_errors": top_errors,
                "emerging_risks": emerging_risks,
                "trend_summary": trend_summary,
                "recommended_actions": recommended_actions,
                "confidence": confidence
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._fallback_analysis(error_stats)
    
    def _fallback_analysis(self, error_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provides fallback analysis when AI is unavailable.
        
        Uses rule-based heuristics to provide basic trend insights.
        """
        top_errors = []
        for error in error_stats.get('top_errors', [])[:5]:
            top_errors.append({
                "error_code": error['error_code'],
                "count": error['count'],
                "trend": error['trend']
            })
        
        emerging_risks = []
        increasing_errors = [e for e in error_stats.get('top_errors', []) if e.get('trend') == 'INCREASING']
        if increasing_errors:
            emerging_risks.append(f"Increase in {len(increasing_errors)} error type(s)")
        
        overall_trend = error_stats.get('overall_trend', 'STABLE')
        total_errors = error_stats.get('total_current_errors', 0)
        
        if total_errors == 0:
            trend_summary = "No errors detected in the analysis period."
        else:
            trend_summary = f"Overall rejection trend is {overall_trend.lower()}. {total_errors} total errors detected in the period."
        
        recommended_actions = []
        if increasing_errors:
            recommended_actions.append("Address increasing error patterns")
        if total_errors > 0:
            recommended_actions.append("Review and fix common error causes")
            recommended_actions.append("Enable Smart Pre-Check Advisor before submission")
        
        return {
            "top_errors": top_errors,
            "emerging_risks": emerging_risks,
            "trend_summary": trend_summary,
            "recommended_actions": recommended_actions,
            "confidence": 0.5  # Lower confidence without AI
        }
    
    def _get_disabled_response(self) -> Dict[str, Any]:
        """
        Returns response when AI is disabled.
        """
        return {
            "top_errors": [],
            "emerging_risks": [],
            "trend_summary": "AI trend analysis disabled",
            "recommended_actions": [],
            "confidence": 0.0
        }

