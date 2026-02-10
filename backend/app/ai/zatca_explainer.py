"""
ZATCA Error AI Explanation Service.

Provides AI-powered explanations for ZATCA errors using OpenRouter.
Generates plain English and Arabic explanations with step-by-step fix guidance.

CRITICAL: This service is EXPLANATION-ONLY. AI never modifies invoice data,
XML structure, tax values, hashes, signatures, or any ZATCA-critical operations.
"""

import logging
from typing import Dict, Optional, List
import json

from app.core.config import get_settings
from app.services.ai.openrouter_service import get_openrouter_service
from app.integrations.zatca.error_catalog import get_error_info, extract_error_code_from_message

logger = logging.getLogger(__name__)


class ZATCAErrorExplainer:
    """
    AI-powered ZATCA error explanation service.
    
    Uses OpenAI GPT-4o to generate:
    - Plain English explanations
    - Optional Arabic explanations
    - Step-by-step fix guidance
    
    CRITICAL: This service only generates explanations. It does NOT modify
    any invoice data, XML, tax values, hashes, or signatures.
    """
    
    def __init__(
        self,
        model: Optional[str] = None
    ):
        """
        Initializes ZATCA error explainer.
        
        Args:
            model: OpenRouter model name (uses default from config if not provided)
        """
        settings = get_settings()
        
        # CRITICAL: Check global AI toggle first
        if not settings.enable_ai_explanation:
            logger.info("AI explanations are globally disabled (ENABLE_AI_EXPLANATION=false). AI will not be invoked.")
            self.openrouter = None
            self.ai_enabled = False
            return
        
        self.ai_enabled = True
        self.model = model or settings.openrouter_default_model
        
        # Get OpenRouter service
        try:
            self.openrouter = get_openrouter_service()
            if not self.openrouter.api_key:
                logger.warning("OpenRouter API key not configured. AI explanations will not work.")
                self.openrouter = None
        except Exception as e:
            logger.warning(f"Failed to initialize OpenRouter service: {e}")
            self.openrouter = None
    
    async def explain_error(
        self,
        error_response: Dict[str, str],
        include_arabic: bool = True,
        preferred_language: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generates AI-powered explanation for ZATCA error.
        
        CRITICAL: This method only generates explanations. It does NOT modify
        invoice data, XML, tax values, hashes, or signatures.
        
        Args:
            error_response: ZATCA error response dictionary containing:
                - error_code (optional): ZATCA error code
                - error (optional): Error message
                - status (optional): Error status
                - Any other error-related fields
            include_arabic: Whether to include Arabic explanation
        
        Returns:
            Dictionary containing:
                - english_explanation: Plain English explanation
                - arabic_explanation: Arabic explanation (if requested)
                - fix_steps: List of step-by-step fix guidance
                - error_code: Detected or provided error code
        """
        # CRITICAL: Check if AI is globally disabled
        if not self.ai_enabled:
            logger.info("AI explanation skipped: AI is globally disabled (ENABLE_AI_EXPLANATION=false)")
            return self._fallback_explanation(error_response)
        
        if not self.openrouter:
            return self._fallback_explanation(error_response)
        
        # Extract error code from response
        error_code = error_response.get("error_code")
        if not error_code:
            error_message = error_response.get("error", "") or error_response.get("error_message", "")
            if error_message:
                error_code = extract_error_code_from_message(error_message)
        
        # Get rule-based error info first (for context)
        rule_based_info = None
        if error_code:
            rule_based_info = get_error_info(error_code)
        
        # Build prompt for AI - prioritize Arabic if requested
        prompt = self._build_explanation_prompt(
            error_response, 
            error_code, 
            rule_based_info, 
            include_arabic,
            preferred_language
        )
        
        try:
            # Call OpenRouter API
            response = await self.openrouter.call_openrouter(
                prompt=prompt,
                model=self.model,
                system_prompt=self._get_system_prompt(),
                temperature=0.3,  # Lower temperature for more consistent, factual responses
                max_tokens=1500
            )
            
            # Parse AI response
            ai_content = response["content"]
            
            # Log token usage (for monitoring, not stored in DB per requirements)
            usage = response.get("usage", {})
            logger.debug(
                f"OpenRouter token usage: prompt={usage.get('prompt_tokens', 0)}, "
                f"completion={usage.get('completion_tokens', 0)}, total={usage.get('total_tokens', 0)}"
            )
            
            return self._parse_ai_response(ai_content, error_code, error_response, include_arabic)
            
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}")
            return self._fallback_explanation(error_response)
    
    def _get_system_prompt(self) -> str:
        """
        Returns system prompt that enforces explanation-only behavior.
        
        CRITICAL: This prompt explicitly prohibits any data modification.
        """
        return """You are a ZATCA (Zakat, Tax and Customs Authority) error explanation assistant.

CRITICAL RULES - YOU MUST FOLLOW THESE STRICTLY:

1. EXPLANATION ONLY: You ONLY generate explanations. You NEVER modify, calculate, or change:
   - Invoice values (quantities, prices, amounts)
   - Tax calculations or tax rates
   - XML structure or content
   - Hash values or digital signatures
   - UUIDs or invoice identifiers
   - Any ZATCA-critical data

2. YOUR ROLE: Provide clear, helpful explanations in:
   - Plain English
   - Arabic (if requested)
   - Step-by-step fix guidance

3. DO NOT:
   - Generate or modify XML
   - Calculate tax amounts
   - Create hash values
   - Modify invoice data
   - Generate signatures

4. DO:
   - Explain what the error means
   - Explain why it occurred
   - Provide step-by-step guidance on how to fix it
   - Use clear, professional language
   - Reference ZATCA requirements when relevant

Remember: You are an EXPLANATION assistant, not a data modification tool."""
    
    def _build_explanation_prompt(
        self,
        error_response: Dict[str, str],
        error_code: Optional[str],
        rule_based_info: Optional[Dict[str, str]],
        include_arabic: bool,
        preferred_language: Optional[str] = None
    ) -> str:
        """Builds prompt for AI explanation."""
        prompt_parts = []
        
        prompt_parts.append("Explain the following ZATCA error:")
        prompt_parts.append("")
        
        if error_code:
            prompt_parts.append(f"Error Code: {error_code}")
        
        if rule_based_info:
            prompt_parts.append("")
            prompt_parts.append("Rule-based error information:")
            prompt_parts.append(f"- Explanation: {rule_based_info.get('explanation', 'N/A')}")
            prompt_parts.append(f"- Technical Reason: {rule_based_info.get('technical_reason', 'N/A')}")
            prompt_parts.append(f"- Corrective Action: {rule_based_info.get('corrective_action', 'N/A')}")
            prompt_parts.append("")
            prompt_parts.append("Use this as context, but provide a more detailed, user-friendly explanation.")
        
        error_message = error_response.get("error") or error_response.get("error_message", "")
        if error_message:
            prompt_parts.append(f"Error Message: {error_message}")
        
        status = error_response.get("status")
        if status:
            prompt_parts.append(f"Status: {status}")
        
        prompt_parts.append("")
        prompt_parts.append("Please provide:")
        
        # Prioritize Arabic if requested
        if preferred_language == "ar" and include_arabic:
            prompt_parts.append("1. An Arabic explanation FIRST (شرح بالعربية) - this is the PRIMARY language")
            prompt_parts.append("2. An English explanation (secondary)")
        else:
            prompt_parts.append("1. A clear, plain English explanation of what this error means")
            if include_arabic:
                prompt_parts.append("2. An Arabic explanation (شرح بالعربية)")
        
        prompt_parts.append("3. Step-by-step guidance on how to fix this error")
        prompt_parts.append("")
        prompt_parts.append("IMPORTANT: Only provide explanations and guidance. Do NOT generate or modify any invoice data, XML, tax values, hashes, or signatures.")
        
        return "\n".join(prompt_parts)
    
    def _parse_ai_response(
        self,
        ai_content: str,
        error_code: Optional[str],
        error_response: Dict[str, str],
        include_arabic: bool
    ) -> Dict[str, str]:
        """
        Parses AI response into structured format.
        
        Attempts to extract English explanation, Arabic explanation, and fix steps.
        """
        result = {
            "error_code": error_code or "UNKNOWN",
            "english_explanation": "",
            "arabic_explanation": "",
            "fix_steps": []
        }
        
        # Try to parse structured response
        # AI might return JSON or plain text
        try:
            # Check if response is JSON
            if ai_content.strip().startswith("{"):
                parsed = json.loads(ai_content)
                result["english_explanation"] = parsed.get("english_explanation", "")
                result["arabic_explanation"] = parsed.get("arabic_explanation", "")
                result["fix_steps"] = parsed.get("fix_steps", [])
                return result
        except json.JSONDecodeError:
            pass
        
        # Parse plain text response
        lines = ai_content.split("\n")
        current_section = None
        english_buffer = []
        arabic_buffer = []
        steps_buffer = []
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Detect sections
            if "english" in line_lower or "explanation" in line_lower and "arabic" not in line_lower:
                current_section = "english"
                continue
            elif "arabic" in line_lower or "عربي" in line or "شرح" in line:
                current_section = "arabic"
                continue
            elif "step" in line_lower or "fix" in line_lower or "guidance" in line_lower:
                current_section = "steps"
                continue
            elif line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "-", "*")):
                current_section = "steps"
            
            # Collect content
            if current_section == "english" and line.strip():
                english_buffer.append(line.strip())
            elif current_section == "arabic" and line.strip() and include_arabic:
                arabic_buffer.append(line.strip())
            elif current_section == "steps" and line.strip():
                # Clean step markers
                step_text = line.strip()
                for prefix in ["1.", "2.", "3.", "4.", "5.", "-", "*", "•"]:
                    if step_text.startswith(prefix):
                        step_text = step_text[len(prefix):].strip()
                if step_text:
                    steps_buffer.append(step_text)
        
        # If no structured parsing, use full content as English explanation
        if not english_buffer and not steps_buffer:
            result["english_explanation"] = ai_content.strip()
        else:
            result["english_explanation"] = " ".join(english_buffer) if english_buffer else ai_content.strip()
            result["arabic_explanation"] = " ".join(arabic_buffer) if arabic_buffer else ""
            result["fix_steps"] = steps_buffer if steps_buffer else []
        
        return result
    
    def _fallback_explanation(self, error_response: Dict[str, str]) -> Dict[str, str]:
        """
        Provides fallback explanation when AI is unavailable.
        
        Uses rule-based error catalog as fallback.
        """
        error_code = error_response.get("error_code")
        if not error_code:
            error_message = error_response.get("error", "") or error_response.get("error_message", "")
            if error_message:
                error_code = extract_error_code_from_message(error_message)
        
        if error_code:
            error_info = get_error_info(error_code)
            if error_info:
                return {
                    "error_code": error_code,
                    "english_explanation": error_info.get("explanation", "Error explanation not available"),
                    "arabic_explanation": "",  # Rule-based catalog doesn't have Arabic
                    "fix_steps": [error_info.get("corrective_action", "Review error and consult ZATCA documentation")]
                }
        
        return {
            "error_code": error_code or "UNKNOWN",
            "english_explanation": "AI explanation service is not available. Please refer to ZATCA documentation for error details.",
            "arabic_explanation": "",
            "fix_steps": ["Review the error message", "Consult ZATCA documentation", "Contact ZATCA support if needed"]
        }

