"""
Invoice Pre-Check Advisor AI Service.

Provides AI-powered pre-check analysis of ZATCA invoices BEFORE submission.
Uses OpenRouter to identify risky fields and patterns with actionable warnings.

CRITICAL: This service is ADVISORY-ONLY and READ-ONLY. AI never modifies invoice data,
XML structure, tax values, hashes, signatures, or any ZATCA-critical operations.
"""

import logging
from typing import Dict, Optional, List, Any
import json

from app.core.config import get_settings
from app.services.ai.openrouter_service import get_openrouter_service

logger = logging.getLogger(__name__)


class PrecheckAdvisor:
    """
    AI-powered invoice pre-check advisor service.
    
    Uses OpenAI GPT-4o to analyze invoice payload and identify:
    - Risky fields and patterns
    - VAT inconsistencies
    - Missing mandatory fields
    - Rounding issues
    - Tax category problems
    
    CRITICAL: This service only generates warnings and advisories. It does NOT modify
    any invoice data, XML, tax values, hashes, or signatures.
    """
    
    def __init__(
        self,
        model: Optional[str] = None
    ):
        """
        Initializes pre-check advisor.
        
        Args:
            model: OpenRouter model name (uses default from config if not provided)
        """
        settings = get_settings()
        
        # CRITICAL: Check global AI toggle first
        if not settings.enable_ai_explanation:
            logger.info("AI pre-check advisor is globally disabled (ENABLE_AI_EXPLANATION=false). AI will not be invoked.")
            self.openrouter = None
            self.ai_enabled = False
            return
        
        self.ai_enabled = True
        self.model = model or settings.openrouter_default_model
        
        # Get OpenRouter service
        try:
            self.openrouter = get_openrouter_service()
            if not self.openrouter.api_key:
                logger.warning("OpenRouter API key not configured. AI pre-check advisor will not work.")
                self.openrouter = None
        except Exception as e:
            logger.warning(f"Failed to initialize OpenRouter service: {e}")
            self.openrouter = None
    
    async def analyze_invoice(
        self,
        invoice_payload: Dict[str, Any],
        environment: str
    ) -> Dict[str, Any]:
        """
        Analyzes invoice payload and returns warnings and risk fields.
        
        CRITICAL: This method only generates warnings. It does NOT modify
        invoice data, XML, tax values, hashes, or signatures.
        
        Args:
            invoice_payload: Invoice payload dictionary (read-only)
            environment: Target environment (SANDBOX or PRODUCTION)
        
        Returns:
            Dictionary containing:
                - warnings: List of human-readable warnings
                - risk_fields: List of JSONPath-like strings pointing to risky fields
                - advisory_notes: Short summary note
        """
        # CRITICAL: Check if AI is globally disabled
        if not self.ai_enabled:
            logger.info("AI pre-check advisor skipped: AI is globally disabled (ENABLE_AI_EXPLANATION=false)")
            return self._get_disabled_response()
        
        if not self.openrouter:
            return self._get_disabled_response()
        
        # Perform rule-based precheck
        rule_based_signals = self._rule_based_precheck(invoice_payload)
        
        # Build prompt for AI
        prompt = self._build_analysis_prompt(
            invoice_payload,
            rule_based_signals,
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
            
            return self._parse_ai_response(ai_content, rule_based_signals)
            
        except Exception as e:
            logger.error(f"Error calling OpenRouter API for pre-check advisor: {e}")
            return self._fallback_analysis(rule_based_signals)
    
    def _rule_based_precheck(self, invoice_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs rule-based precheck to identify obvious issues.
        
        Returns signals that can be combined with AI analysis.
        """
        signals = {
            "warnings": [],
            "risk_fields": [],
            "checks_passed": []
        }
        
        # Check VAT number format (15 digits)
        seller_tax_number = invoice_payload.get("seller_tax_number", "")
        if seller_tax_number:
            if len(seller_tax_number) != 15 or not seller_tax_number.isdigit():
                signals["warnings"].append("Invalid seller VAT number format (must be 15 digits)")
                signals["risk_fields"].append("seller_tax_number")
            else:
                signals["checks_passed"].append("Seller VAT number format valid")
        
        buyer_tax_number = invoice_payload.get("buyer_tax_number", "")
        if buyer_tax_number:
            if len(buyer_tax_number) != 15 or not buyer_tax_number.isdigit():
                signals["warnings"].append("Buyer VAT number format may be invalid (should be 15 digits if provided)")
                signals["risk_fields"].append("buyer_tax_number")
        
        # Check required fields
        required_fields = {
            "invoice_number": "Invoice number",
            "invoice_date": "Invoice date",
            "seller_name": "Seller name",
            "seller_tax_number": "Seller VAT number",
            "line_items": "Line items"
        }
        
        for field, name in required_fields.items():
            if field not in invoice_payload or not invoice_payload[field]:
                signals["warnings"].append(f"Missing required field: {name}")
                signals["risk_fields"].append(field)
        
        # Check totals consistency
        total_tax_exclusive = invoice_payload.get("total_tax_exclusive", 0)
        total_tax_amount = invoice_payload.get("total_tax_amount", 0)
        total_amount = invoice_payload.get("total_amount", 0)
        
        calculated_total = total_tax_exclusive + total_tax_amount
        if total_amount > 0 and abs(calculated_total - total_amount) > 0.01:
            signals["warnings"].append(
                f"Total amount mismatch: total_amount ({total_amount}) != "
                f"total_tax_exclusive ({total_tax_exclusive}) + total_tax_amount ({total_tax_amount})"
            )
            signals["risk_fields"].extend(["total_amount", "total_tax_exclusive", "total_tax_amount"])
        
        # Check line items
        line_items = invoice_payload.get("line_items", [])
        if not line_items:
            signals["warnings"].append("No line items provided")
            signals["risk_fields"].append("line_items")
        else:
            signals["checks_passed"].append(f"Line items present ({len(line_items)} items)")
            
            # Check line item consistency
            for idx, item in enumerate(line_items):
                item_taxable = item.get("taxable_amount", 0)
                item_tax = item.get("tax_amount", 0)
                item_total = item.get("total", item_taxable + item_tax)
                
                calculated_item_total = item_taxable + item_tax
                if abs(item_total - calculated_item_total) > 0.01:
                    signals["warnings"].append(
                        f"Line item {idx + 1} total mismatch: "
                        f"total ({item_total}) != taxable_amount ({item_taxable}) + tax_amount ({item_tax})"
                    )
                    signals["risk_fields"].append(f"line_items[{idx}].total")
        
        return signals
    
    def _get_system_prompt(self) -> str:
        """
        Returns system prompt that enforces advisory-only behavior.
        
        CRITICAL: This prompt explicitly prohibits any data modification.
        """
        return """You are a ZATCA (Zakat, Tax and Customs Authority) invoice pre-check advisor assistant.

CRITICAL RULES - YOU MUST FOLLOW THESE STRICTLY:

1. ADVISORY ONLY: You ONLY generate warnings and risk field pointers. You NEVER modify, calculate, or change:
   - Invoice values (quantities, prices, amounts)
   - Tax calculations or tax rates
   - XML structure or content
   - Hash values or digital signatures
   - UUIDs or invoice identifiers
   - Any ZATCA-critical data

2. YOUR ROLE: Analyze invoice payload and identify:
   - Risky fields and patterns
   - VAT inconsistencies
   - Missing mandatory fields
   - Rounding issues
   - Tax category problems
   - Provide actionable warnings with field pointers

3. DO NOT:
   - Generate or modify XML
   - Calculate tax amounts
   - Create hash values
   - Modify invoice data
   - Generate signatures
   - Block or prevent submission

4. DO:
   - Identify risky fields using JSONPath-like notation (e.g., "line_items[2].tax_percent", "buyer_tax_number")
   - Provide clear, actionable warnings
   - Point to specific fields that need attention
   - Consider ZATCA compliance requirements

5. RESPONSE FORMAT: You MUST return valid JSON with this exact structure:
{
  "warnings": ["warning1", "warning2", ...],
  "risk_fields": ["field.path.1", "field.path.2", ...],
  "advisory_notes": "Short summary note"
}

6. RISK FIELD NOTATION:
   - Use dot notation for nested fields: "seller.tax_number"
   - Use array notation for lists: "line_items[0].tax_percent"
   - Use descriptive paths that match the invoice structure

Remember: You are an ADVISORY assistant, not a data modification tool."""
    
    def _build_analysis_prompt(
        self,
        invoice_payload: Dict[str, Any],
        rule_based_signals: Dict[str, Any],
        environment: str
    ) -> str:
        """Builds prompt for AI analysis."""
        prompt_parts = []
        
        prompt_parts.append("Analyze the following invoice payload and identify risky fields and patterns:")
        prompt_parts.append("")
        prompt_parts.append("INVOICE PAYLOAD (read-only, for analysis only):")
        prompt_parts.append(json.dumps(invoice_payload, indent=2, default=str))
        prompt_parts.append("")
        
        prompt_parts.append("RULE-BASED PRECHECK SIGNALS:")
        if rule_based_signals.get("warnings"):
            prompt_parts.append("Warnings found:")
            for warning in rule_based_signals["warnings"]:
                prompt_parts.append(f"  - {warning}")
        if rule_based_signals.get("risk_fields"):
            prompt_parts.append("Risk fields identified:")
            for field in rule_based_signals["risk_fields"]:
                prompt_parts.append(f"  - {field}")
        if rule_based_signals.get("checks_passed"):
            prompt_parts.append("Checks passed:")
            for check in rule_based_signals["checks_passed"]:
                prompt_parts.append(f"  - {check}")
        prompt_parts.append("")
        
        prompt_parts.append("TARGET ENVIRONMENT: " + environment)
        prompt_parts.append("")
        
        prompt_parts.append("ANALYSIS SCOPE - Look for:")
        prompt_parts.append("1. VAT percent inconsistencies (line item vs total)")
        prompt_parts.append("2. Missing buyer VAT number for B2B invoices")
        prompt_parts.append("3. Invalid or missing tax categories")
        prompt_parts.append("4. Rounding inconsistencies in totals")
        prompt_parts.append("5. Missing mandatory fields (dates, currency, totals)")
        prompt_parts.append("6. Suspicious zero tax where VAT expected")
        prompt_parts.append("7. Tax rate mismatches across line items")
        prompt_parts.append("8. Invalid date formats or future dates")
        prompt_parts.append("9. Currency code issues")
        prompt_parts.append("10. Line item calculation errors")
        prompt_parts.append("")
        
        prompt_parts.append("Please provide a JSON response with:")
        prompt_parts.append("1. warnings: Array of human-readable warning messages")
        prompt_parts.append("2. risk_fields: Array of JSONPath-like strings pointing to risky fields")
        prompt_parts.append("3. advisory_notes: Short summary note for the user")
        prompt_parts.append("")
        prompt_parts.append("IMPORTANT: Only provide warnings and field pointers. Do NOT generate or modify any invoice data, XML, tax values, hashes, or signatures.")
        
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
            
            warnings = parsed.get("warnings", [])
            if not isinstance(warnings, list):
                warnings = []
            
            risk_fields = parsed.get("risk_fields", [])
            if not isinstance(risk_fields, list):
                risk_fields = []
            
            advisory_notes = parsed.get("advisory_notes", "")
            
            # Merge with rule-based signals (avoid duplicates)
            rule_warnings = rule_based_signals.get("warnings", [])
            rule_risk_fields = rule_based_signals.get("risk_fields", [])
            
            # Combine warnings (avoid duplicates)
            all_warnings = list(warnings)
            for rule_warning in rule_warnings:
                if rule_warning not in all_warnings:
                    all_warnings.append(rule_warning)
            
            # Combine risk fields (avoid duplicates)
            all_risk_fields = list(risk_fields)
            for rule_field in rule_risk_fields:
                if rule_field not in all_risk_fields:
                    all_risk_fields.append(rule_field)
            
            # Generate advisory notes if not provided
            if not advisory_notes:
                if all_warnings:
                    advisory_notes = f"Found {len(all_warnings)} issue(s) that may cause rejection. Review the warnings and fix the identified risk fields before submission."
                else:
                    advisory_notes = "No issues detected. Invoice appears compliant, but please verify all fields before submission."
            
            # Determine risk score based on warnings
            if len(all_warnings) >= 5:
                risk_score = "HIGH"
            elif len(all_warnings) >= 2:
                risk_score = "MEDIUM"
            elif len(all_warnings) > 0:
                risk_score = "LOW"
            else:
                risk_score = "LOW"
            
            return {
                "risk_score": risk_score,
                "warnings": all_warnings,
                "risk_fields": all_risk_fields,
                "advisory_notes": advisory_notes
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._fallback_analysis(rule_based_signals)
    
    def _fallback_analysis(self, rule_based_signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provides fallback analysis when AI is unavailable.
        
        Uses rule-based signals to provide basic warnings.
        ALWAYS returns full schema including risk_score.
        """
        warnings = rule_based_signals.get("warnings", [])
        risk_fields = rule_based_signals.get("risk_fields", [])
        
        if warnings:
            advisory_notes = f"Found {len(warnings)} issue(s) using rule-based checks. AI analysis unavailable - manual review recommended."
        else:
            advisory_notes = "Basic checks passed. AI analysis unavailable - manual review recommended before submission."
        
        return {
            "risk_score": "UNKNOWN",
            "warnings": warnings,
            "risk_fields": risk_fields,
            "advisory_notes": advisory_notes
        }
    
    def _get_disabled_response(self) -> Dict[str, Any]:
        """
        Returns response when AI is disabled.
        ALWAYS returns full schema including risk_score.
        """
        return {
            "risk_score": "UNKNOWN",
            "warnings": [],
            "risk_fields": [],
            "advisory_notes": "AI pre-check advisor is disabled."
        }

