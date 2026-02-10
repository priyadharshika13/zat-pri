"""
ZATCA Environment and Invoice-Type Policy Enforcement Service.

Enforces strict ZATCA production rules for invoice processing based on environment
and invoice type. Prevents invalid flows before calling ZATCA APIs.

CRITICAL: Production must strictly follow ZATCA rules:
- SANDBOX: Any invoice type → Clearance + Reporting (allowed)
- PRODUCTION: Standard (388) → Clearance ONLY
- PRODUCTION: Simplified (383) → Reporting ONLY
- PRODUCTION: Mixed flow → Reject
"""

import logging
from typing import Optional
from enum import Enum

from app.core.constants import Environment

logger = logging.getLogger(__name__)


class InvoiceType(str, Enum):
    """ZATCA invoice type codes."""
    STANDARD = "388"  # B2B invoices
    SIMPLIFIED = "383"  # B2C invoices
    DEBIT_NOTE = "381"  # Debit notes


class ZatcaPolicyAction(str, Enum):
    """Allowed actions for invoice processing."""
    CLEARANCE = "CLEARANCE"
    REPORTING = "REPORTING"
    BOTH = "BOTH"  # Clearance + Reporting


class ZatcaPolicyViolation(Exception):
    """Exception raised when ZATCA policy is violated."""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(self.message)


class ZatcaPolicyService:
    """
    Service for enforcing ZATCA environment and invoice-type policies.
    
    CRITICAL: This service prevents invalid invoice flows before they reach ZATCA APIs.
    All policy checks must pass before clearance or reporting operations.
    """
    
    # Policy rules mapping: (environment, invoice_type) -> allowed_actions
    POLICY_RULES = {
        (Environment.SANDBOX, InvoiceType.STANDARD): ZatcaPolicyAction.BOTH,
        (Environment.SANDBOX, InvoiceType.SIMPLIFIED): ZatcaPolicyAction.BOTH,
        (Environment.SANDBOX, InvoiceType.DEBIT_NOTE): ZatcaPolicyAction.BOTH,
        (Environment.PRODUCTION, InvoiceType.STANDARD): ZatcaPolicyAction.CLEARANCE,
        (Environment.PRODUCTION, InvoiceType.SIMPLIFIED): ZatcaPolicyAction.REPORTING,
        (Environment.PRODUCTION, InvoiceType.DEBIT_NOTE): ZatcaPolicyAction.CLEARANCE,
    }
    
    def __init__(self):
        """Initializes ZATCA policy service."""
        pass
    
    def validate_clearance_allowed(
        self,
        environment: Environment,
        invoice_type: str
    ) -> None:
        """
        Validates that clearance is allowed for the given environment and invoice type.
        
        Policy Rules:
        - SANDBOX: Clearance allowed for all invoice types
        - PRODUCTION: Clearance allowed ONLY for Standard (388) and Debit Note (381)
        - PRODUCTION: Clearance NOT allowed for Simplified (383)
        
        Args:
            environment: Target environment (SANDBOX or PRODUCTION)
            invoice_type: Invoice type code (388, 383, or 381)
            
        Raises:
            ZatcaPolicyViolation: If clearance is not allowed
        """
        # Normalize invoice type
        invoice_type_enum = self._parse_invoice_type(invoice_type)
        if invoice_type_enum is None:
            raise ZatcaPolicyViolation(
                error_code="ZATCA_POLICY_VIOLATION",
                message=f"Invalid invoice type: {invoice_type}. Must be 388 (Standard), 383 (Simplified), or 381 (Debit Note)"
            )
        
        # Get allowed actions for this environment/invoice type combination
        allowed_actions = self.POLICY_RULES.get((environment, invoice_type_enum))
        
        if allowed_actions is None:
            # Unknown combination - reject for safety
            raise ZatcaPolicyViolation(
                error_code="ZATCA_POLICY_VIOLATION",
                message=f"Unknown policy rule for environment={environment.value}, invoice_type={invoice_type}"
            )
        
        # Check if clearance is allowed
        if allowed_actions not in (ZatcaPolicyAction.CLEARANCE, ZatcaPolicyAction.BOTH):
            raise ZatcaPolicyViolation(
                error_code="ZATCA_POLICY_VIOLATION",
                message=(
                    f"Clearance is not allowed for {invoice_type_enum.value} invoices in {environment.value}. "
                    f"Standard invoices (388) can only be cleared in production. "
                    f"Simplified invoices (383) can only be reported in production."
                )
            )
        
        logger.debug(
            f"Clearance policy check passed: environment={environment.value}, "
            f"invoice_type={invoice_type}, allowed_actions={allowed_actions.value}"
        )
    
    def validate_reporting_allowed(
        self,
        environment: Environment,
        invoice_type: str
    ) -> None:
        """
        Validates that reporting is allowed for the given environment and invoice type.
        
        Policy Rules:
        - SANDBOX: Reporting allowed for all invoice types
        - PRODUCTION: Reporting allowed ONLY for Simplified (383)
        - PRODUCTION: Reporting NOT allowed for Standard (388) or Debit Note (381)
        
        Args:
            environment: Target environment (SANDBOX or PRODUCTION)
            invoice_type: Invoice type code (388, 383, or 381)
            
        Raises:
            ZatcaPolicyViolation: If reporting is not allowed
        """
        # Normalize invoice type
        invoice_type_enum = self._parse_invoice_type(invoice_type)
        if invoice_type_enum is None:
            raise ZatcaPolicyViolation(
                error_code="ZATCA_POLICY_VIOLATION",
                message=f"Invalid invoice type: {invoice_type}. Must be 388 (Standard), 383 (Simplified), or 381 (Debit Note)"
            )
        
        # Get allowed actions for this environment/invoice type combination
        allowed_actions = self.POLICY_RULES.get((environment, invoice_type_enum))
        
        if allowed_actions is None:
            # Unknown combination - reject for safety
            raise ZatcaPolicyViolation(
                error_code="ZATCA_POLICY_VIOLATION",
                message=f"Unknown policy rule for environment={environment.value}, invoice_type={invoice_type}"
            )
        
        # Check if reporting is allowed
        if allowed_actions not in (ZatcaPolicyAction.REPORTING, ZatcaPolicyAction.BOTH):
            raise ZatcaPolicyViolation(
                error_code="ZATCA_POLICY_VIOLATION",
                message=(
                    f"Reporting is not allowed for {invoice_type_enum.value} invoices in {environment.value}. "
                    f"Simplified invoices (383) can only be reported in production. "
                    f"Standard invoices (388) can only be cleared in production."
                )
            )
        
        logger.debug(
            f"Reporting policy check passed: environment={environment.value}, "
            f"invoice_type={invoice_type}, allowed_actions={allowed_actions.value}"
        )
    
    def validate_clearance_and_reporting_allowed(
        self,
        environment: Environment,
        invoice_type: str
    ) -> None:
        """
        Validates that both clearance AND reporting are allowed.
        
        This is used when an invoice flow requires both operations (e.g., automatic
        reporting after clearance).
        
        Policy Rules:
        - SANDBOX: Both allowed for all invoice types
        - PRODUCTION: Both NOT allowed (mixed flow rejected)
        
        Args:
            environment: Target environment (SANDBOX or PRODUCTION)
            invoice_type: Invoice type code (388, 383, or 381)
            
        Raises:
            ZatcaPolicyViolation: If both clearance and reporting are not allowed
        """
        # Normalize invoice type
        invoice_type_enum = self._parse_invoice_type(invoice_type)
        if invoice_type_enum is None:
            raise ZatcaPolicyViolation(
                error_code="ZATCA_POLICY_VIOLATION",
                message=f"Invalid invoice type: {invoice_type}. Must be 388 (Standard), 383 (Simplified), or 381 (Debit Note)"
            )
        
        # Get allowed actions for this environment/invoice type combination
        allowed_actions = self.POLICY_RULES.get((environment, invoice_type_enum))
        
        if allowed_actions is None:
            # Unknown combination - reject for safety
            raise ZatcaPolicyViolation(
                error_code="ZATCA_POLICY_VIOLATION",
                message=f"Unknown policy rule for environment={environment.value}, invoice_type={invoice_type}"
            )
        
        # Check if both clearance and reporting are allowed
        if allowed_actions != ZatcaPolicyAction.BOTH:
            raise ZatcaPolicyViolation(
                error_code="ZATCA_POLICY_VIOLATION",
                message=(
                    f"Mixed flow (clearance + reporting) is not allowed for {invoice_type_enum.value} invoices "
                    f"in {environment.value}. "
                    f"In production, Standard invoices (388) can only be cleared, "
                    f"and Simplified invoices (383) can only be reported."
                )
            )
        
        logger.debug(
            f"Clearance+Reporting policy check passed: environment={environment.value}, "
            f"invoice_type={invoice_type}, allowed_actions={allowed_actions.value}"
        )
    
    def get_allowed_actions(
        self,
        environment: Environment,
        invoice_type: str
    ) -> ZatcaPolicyAction:
        """
        Gets allowed actions for the given environment and invoice type.
        
        Args:
            environment: Target environment (SANDBOX or PRODUCTION)
            invoice_type: Invoice type code (388, 383, or 381)
            
        Returns:
            ZatcaPolicyAction indicating what operations are allowed
            
        Raises:
            ZatcaPolicyViolation: If invoice type is invalid
        """
        # Normalize invoice type
        invoice_type_enum = self._parse_invoice_type(invoice_type)
        if invoice_type_enum is None:
            raise ZatcaPolicyViolation(
                error_code="ZATCA_POLICY_VIOLATION",
                message=f"Invalid invoice type: {invoice_type}. Must be 388 (Standard), 383 (Simplified), or 381 (Debit Note)"
            )
        
        # Get allowed actions
        allowed_actions = self.POLICY_RULES.get((environment, invoice_type_enum))
        
        if allowed_actions is None:
            # Unknown combination - reject for safety
            raise ZatcaPolicyViolation(
                error_code="ZATCA_POLICY_VIOLATION",
                message=f"Unknown policy rule for environment={environment.value}, invoice_type={invoice_type}"
            )
        
        return allowed_actions
    
    def _parse_invoice_type(self, invoice_type: str) -> Optional[InvoiceType]:
        """
        Parses invoice type string to InvoiceType enum.
        
        Args:
            invoice_type: Invoice type code (string)
            
        Returns:
            InvoiceType enum or None if invalid
        """
        invoice_type_clean = str(invoice_type).strip()
        
        try:
            return InvoiceType(invoice_type_clean)
        except ValueError:
            return None

