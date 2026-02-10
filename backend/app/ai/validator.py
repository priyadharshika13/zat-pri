"""
AI-based invoice validator.

Orchestrates AI validation for invoices using prompt-based validation.
Coordinates between prompt generation and AI client calls.
Does not handle rule-based validation or external API calls directly.
"""

import logging
from typing import Dict

from app.ai.client import AIClient
from app.ai.phase1_prompt import get_phase1_validation_prompt
from app.ai.phase2_prompt import get_phase2_validation_prompt

logger = logging.getLogger(__name__)


class AIValidator:
    """Validates invoices using AI-based validation."""
    
    def __init__(self, ai_client: AIClient = None):
        """
        Initializes AI validator.
        
        Args:
            ai_client: AI client instance
        """
        self.ai_client = ai_client or AIClient()
    
    async def validate_phase1(self, invoice_data: Dict) -> Dict:
        """
        Validates Phase-1 invoice using AI.
        
        Args:
            invoice_data: Invoice data dictionary
            
        Returns:
            Dictionary containing validation results
        """
        logger.debug("Validating Phase-1 invoice with AI")
        prompt = get_phase1_validation_prompt(invoice_data)
        return await self.ai_client.validate(prompt, invoice_data)
    
    async def validate_phase2(self, invoice_data: Dict) -> Dict:
        """
        Validates Phase-2 invoice using AI.
        
        Args:
            invoice_data: Invoice data dictionary
            
        Returns:
            Dictionary containing validation results
        """
        logger.debug("Validating Phase-2 invoice with AI")
        prompt = get_phase2_validation_prompt(invoice_data)
        return await self.ai_client.validate(prompt, invoice_data)

