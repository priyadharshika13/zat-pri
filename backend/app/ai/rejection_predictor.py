"""
Invoice Rejection Prediction AI Service.

Provides AI-powered prediction of ZATCA invoice rejection likelihood BEFORE submission.
Uses OpenRouter to analyze invoice payload and predict rejection risk.

CRITICAL: This service is PREDICTION-ONLY. AI never modifies invoice data,
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


class InvoiceRejectionPredictor:
    """
    AI-powered invoice rejection prediction service.
    
    Uses OpenAI GPT-4o to predict rejection likelihood by analyzing:
    - Invoice payload structure and values
    - Historical tenant rejection patterns
    - Common ZATCA rejection causes
    
    CRITICAL: This service only generates predictions. It does NOT modify
    any invoice data, XML, tax values, hashes, or signatures.
    """
    
    def __init__(
        self,
        model: Optional[str] = None
    ):
        """
        Initializes invoice rejection predictor.
        
        Args:
            model: OpenRouter model name (uses default from config if not provided)
        """
        settings = get_settings()
        
        # CRITICAL: Check global AI toggle first
        if not settings.enable_ai_explanation:
            logger.info("AI predictions are globally disabled (ENABLE_AI_EXPLANATION=false). AI will not be invoked.")
            self.openrouter = None
            self.ai_enabled = False
            return
        
        self.ai_enabled = True
        self.model = model or settings.openrouter_default_model
        
        # Get OpenRouter service
        try:
            self.openrouter = get_openrouter_service()
            if not self.openrouter.api_key:
                logger.warning("OpenRouter API key not configured. AI predictions will not work.")
                self.openrouter = None
        except Exception as e:
            logger.warning(f"Failed to initialize OpenRouter service: {e}")
            self.openrouter = None
    
    async def predict_rejection(
        self,
        invoice_payload: Dict[str, Any],
        tenant_context: TenantContext,
        db: Session,
        environment: str
    ) -> Dict[str, Any]:
        """
        Predicts likelihood of ZATCA invoice rejection.
        
        CRITICAL: This method only generates predictions. It does NOT modify
        invoice data, XML, tax values, hashes, or signatures.
        
        Args:
            invoice_payload: Invoice payload dictionary (read-only)
            tenant_context: Tenant context for historical analysis
            db: Database session for querying historical patterns
            environment: Target environment (SANDBOX or PRODUCTION)
        
        Returns:
            Dictionary containing:
                - risk_level: LOW, MEDIUM, HIGH, or UNKNOWN
                - confidence: float (0.0 to 1.0)
                - likely_reasons: List of likely rejection reasons
                - advisory_note: Short human-readable message
        """
        # CRITICAL: Check if AI is globally disabled
        if not self.ai_enabled:
            logger.info("AI prediction skipped: AI is globally disabled (ENABLE_AI_EXPLANATION=false)")
            return self._get_disabled_response()
        
        if not self.openrouter:
            return self._get_disabled_response()
        
        # Get historical rejection patterns for this tenant
        historical_context = self._get_historical_context(tenant_context, db, environment)
        
        # Perform rule-based precheck
        rule_based_signals = self._rule_based_precheck(invoice_payload)
        
        # Build prompt for AI
        prompt = self._build_prediction_prompt(
            invoice_payload,
            historical_context,
            rule_based_signals,
            environment
        )
        
        try:
            # Call OpenRouter API
            response = await self.openrouter.call_openrouter(
                prompt=prompt,
                model=self.model,
                system_prompt=self._get_system_prompt(),
                temperature=0.2,  # Lower temperature for more consistent, factual predictions
                max_tokens=1000,
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
            
            return self._parse_ai_response(ai_content, rule_based_signals)
            
        except Exception as e:
            logger.error(f"Error calling OpenRouter API for rejection prediction: {e}")
            return self._fallback_prediction(rule_based_signals)
    
    def _get_historical_context(
        self,
        tenant_context: TenantContext,
        db: Session,
        environment: str
    ) -> Dict[str, Any]:
        """
        Gets historical rejection patterns for the tenant.
        
        Returns aggregated statistics without exposing invoice data.
        """
        try:
            # Get rejection rate in last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            # Total submissions
            total_submissions = db.query(func.count(InvoiceLog.id)).filter(
                InvoiceLog.tenant_id == tenant_context.tenant_id,
                InvoiceLog.environment == environment,
                InvoiceLog.created_at >= thirty_days_ago
            ).scalar() or 0
            
            # Rejections
            rejections = db.query(func.count(InvoiceLog.id)).filter(
                InvoiceLog.tenant_id == tenant_context.tenant_id,
                InvoiceLog.environment == environment,
                InvoiceLog.status == InvoiceLogStatus.REJECTED,
                InvoiceLog.created_at >= thirty_days_ago
            ).scalar() or 0
            
            # Most common rejection codes (top 3)
            common_codes = db.query(
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
            ).limit(3).all()
            
            rejection_rate = (rejections / total_submissions * 100) if total_submissions > 0 else 0.0
            
            return {
                "total_submissions_30d": total_submissions,
                "rejections_30d": rejections,
                "rejection_rate_30d": round(rejection_rate, 2),
                "common_rejection_codes": [code for code, _ in common_codes] if common_codes else []
            }
        except Exception as e:
            logger.warning(f"Error fetching historical context: {e}")
            return {
                "total_submissions_30d": 0,
                "rejections_30d": 0,
                "rejection_rate_30d": 0.0,
                "common_rejection_codes": []
            }
    
    def _rule_based_precheck(self, invoice_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs rule-based precheck to identify obvious issues.
        
        Returns signals that can be combined with AI analysis.
        """
        signals = {
            "issues": [],
            "warnings": [],
            "checks_passed": []
        }
        
        # Check VAT number format (15 digits)
        seller_tax_number = invoice_payload.get("seller_tax_number", "")
        if seller_tax_number and (len(seller_tax_number) != 15 or not seller_tax_number.isdigit()):
            signals["issues"].append("Invalid seller VAT number format (must be 15 digits)")
        
        buyer_tax_number = invoice_payload.get("buyer_tax_number", "")
        if buyer_tax_number and (len(buyer_tax_number) != 15 or not buyer_tax_number.isdigit()):
            signals["warnings"].append("Buyer VAT number format may be invalid (should be 15 digits if provided)")
        
        # Check required fields
        required_fields = ["invoice_number", "invoice_date", "seller_name", "seller_tax_number", "line_items"]
        for field in required_fields:
            if field not in invoice_payload or not invoice_payload[field]:
                signals["issues"].append(f"Missing required field: {field}")
        
        # Check totals consistency
        total_tax_exclusive = invoice_payload.get("total_tax_exclusive", 0)
        total_tax_amount = invoice_payload.get("total_tax_amount", 0)
        total_amount = invoice_payload.get("total_amount", 0)
        
        calculated_total = total_tax_exclusive + total_tax_amount
        if total_amount > 0 and abs(calculated_total - total_amount) > 0.01:
            signals["issues"].append("Total amount mismatch (total_amount != total_tax_exclusive + total_tax_amount)")
        
        # Check line items
        line_items = invoice_payload.get("line_items", [])
        if not line_items:
            signals["issues"].append("No line items provided")
        else:
            signals["checks_passed"].append(f"Line items present ({len(line_items)} items)")
        
        return signals
    
    def _get_system_prompt(self) -> str:
        """
        Returns system prompt that enforces prediction-only behavior.
        
        CRITICAL: This prompt explicitly prohibits any data modification.
        """
        return """You are a ZATCA (Zakat, Tax and Customs Authority) invoice rejection prediction assistant.

CRITICAL RULES - YOU MUST FOLLOW THESE STRICTLY:

1. PREDICTION ONLY: You ONLY generate risk predictions. You NEVER modify, calculate, or change:
   - Invoice values (quantities, prices, amounts)
   - Tax calculations or tax rates
   - XML structure or content
   - Hash values or digital signatures
   - UUIDs or invoice identifiers
   - Any ZATCA-critical data

2. YOUR ROLE: Analyze invoice payload and predict rejection likelihood:
   - Risk level: LOW, MEDIUM, or HIGH
   - Confidence score: 0.0 to 1.0
   - Likely rejection reasons (if any)
   - Advisory note for the user

3. DO NOT:
   - Generate or modify XML
   - Calculate tax amounts
   - Create hash values
   - Modify invoice data
   - Generate signatures
   - Block or prevent submission

4. DO:
   - Analyze invoice structure and values
   - Identify potential compliance issues
   - Consider historical rejection patterns
   - Provide risk assessment
   - Give actionable advisory notes

5. RESPONSE FORMAT: You MUST return valid JSON with this exact structure:
{
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "confidence": 0.0-1.0,
  "likely_reasons": ["reason1", "reason2", ...],
  "advisory_note": "Short human-readable message"
}

Remember: You are a PREDICTION assistant, not a data modification tool."""
    
    def _build_prediction_prompt(
        self,
        invoice_payload: Dict[str, Any],
        historical_context: Dict[str, Any],
        rule_based_signals: Dict[str, Any],
        environment: str
    ) -> str:
        """Builds prompt for AI prediction."""
        prompt_parts = []
        
        prompt_parts.append("Analyze the following invoice payload and predict the likelihood of ZATCA rejection:")
        prompt_parts.append("")
        prompt_parts.append("INVOICE PAYLOAD (read-only, for analysis only):")
        prompt_parts.append(json.dumps(invoice_payload, indent=2, default=str))
        prompt_parts.append("")
        
        prompt_parts.append("HISTORICAL CONTEXT (tenant rejection patterns):")
        prompt_parts.append(f"- Total submissions (last 30 days): {historical_context.get('total_submissions_30d', 0)}")
        prompt_parts.append(f"- Rejections (last 30 days): {historical_context.get('rejections_30d', 0)}")
        prompt_parts.append(f"- Rejection rate: {historical_context.get('rejection_rate_30d', 0.0)}%")
        if historical_context.get('common_rejection_codes'):
            prompt_parts.append(f"- Common rejection codes: {', '.join(historical_context['common_rejection_codes'])}")
        prompt_parts.append("")
        
        prompt_parts.append("RULE-BASED PRECHECK SIGNALS:")
        if rule_based_signals.get("issues"):
            prompt_parts.append(f"- Issues found: {', '.join(rule_based_signals['issues'])}")
        if rule_based_signals.get("warnings"):
            prompt_parts.append(f"- Warnings: {', '.join(rule_based_signals['warnings'])}")
        if rule_based_signals.get("checks_passed"):
            prompt_parts.append(f"- Checks passed: {', '.join(rule_based_signals['checks_passed'])}")
        prompt_parts.append("")
        
        prompt_parts.append("TARGET ENVIRONMENT: " + environment)
        prompt_parts.append("")
        
        prompt_parts.append("COMMON ZATCA REJECTION CAUSES TO CONSIDER:")
        prompt_parts.append("- VAT mismatch or invalid VAT numbers")
        prompt_parts.append("- Missing buyer VAT number (when required)")
        prompt_parts.append("- Invalid tax category codes")
        prompt_parts.append("- Rounding inconsistencies in totals")
        prompt_parts.append("- Invalid document totals")
        prompt_parts.append("- Missing required fields")
        prompt_parts.append("- Invalid date formats")
        prompt_parts.append("- Line item calculation errors")
        prompt_parts.append("")
        
        prompt_parts.append("Please provide a JSON response with:")
        prompt_parts.append("1. risk_level: LOW, MEDIUM, or HIGH")
        prompt_parts.append("2. confidence: A confidence score between 0.0 and 1.0")
        prompt_parts.append("3. likely_reasons: Array of specific reasons if risk is MEDIUM or HIGH")
        prompt_parts.append("4. advisory_note: Short, actionable message for the user")
        prompt_parts.append("")
        prompt_parts.append("IMPORTANT: Only provide predictions. Do NOT generate or modify any invoice data, XML, tax values, hashes, or signatures.")
        
        return "\n".join(prompt_parts)
    
    def _parse_ai_response(
        self,
        ai_content: str,
        rule_based_signals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parses AI response into structured format.
        
        Validates and combines with rule-based signals.
        """
        try:
            # Parse JSON response
            parsed = json.loads(ai_content)
            
            risk_level = parsed.get("risk_level", "UNKNOWN").upper()
            if risk_level not in ["LOW", "MEDIUM", "HIGH", "UNKNOWN"]:
                risk_level = "UNKNOWN"
            
            confidence = float(parsed.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0.0, 1.0]
            
            likely_reasons = parsed.get("likely_reasons", [])
            if not isinstance(likely_reasons, list):
                likely_reasons = []
            
            # Enhance with rule-based issues if present
            if rule_based_signals.get("issues") and risk_level != "HIGH":
                # If rule-based found critical issues, elevate risk
                likely_reasons.extend(rule_based_signals["issues"])
                if risk_level == "LOW":
                    risk_level = "MEDIUM"
            
            advisory_note = parsed.get("advisory_note", "")
            if not advisory_note:
                if risk_level == "HIGH":
                    advisory_note = "High probability of rejection. Please review before submission."
                elif risk_level == "MEDIUM":
                    advisory_note = "Moderate risk of rejection. Review the identified issues before submission."
                elif risk_level == "LOW":
                    advisory_note = "Low risk of rejection. Invoice appears compliant."
                else:
                    advisory_note = "Unable to assess risk. Please review invoice manually."
            
            return {
                "risk_level": risk_level,
                "confidence": confidence,
                "likely_reasons": likely_reasons,
                "advisory_note": advisory_note
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._fallback_prediction(rule_based_signals)
    
    def _fallback_prediction(self, rule_based_signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provides fallback prediction when AI is unavailable.
        
        Uses rule-based signals to provide basic risk assessment.
        """
        issues = rule_based_signals.get("issues", [])
        warnings = rule_based_signals.get("warnings", [])
        
        if issues:
            risk_level = "HIGH" if len(issues) >= 2 else "MEDIUM"
            confidence = 0.7 if risk_level == "HIGH" else 0.5
            likely_reasons = issues + warnings
            advisory_note = "Rule-based checks identified issues. Please review before submission."
        elif warnings:
            risk_level = "MEDIUM"
            confidence = 0.4
            likely_reasons = warnings
            advisory_note = "Some warnings detected. Review recommended before submission."
        else:
            risk_level = "LOW"
            confidence = 0.3  # Lower confidence without AI
            likely_reasons = []
            advisory_note = "Basic checks passed. AI prediction unavailable - manual review recommended."
        
        return {
            "risk_level": risk_level,
            "confidence": confidence,
            "likely_reasons": likely_reasons,
            "advisory_note": advisory_note
        }
    
    def _get_disabled_response(self) -> Dict[str, Any]:
        """
        Returns response when AI is disabled.
        """
        return {
            "risk_level": "UNKNOWN",
            "confidence": 0.0,
            "likely_reasons": [],
            "advisory_note": "AI prediction disabled"
        }

