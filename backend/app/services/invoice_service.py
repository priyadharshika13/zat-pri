"""
Invoice processing service orchestrator.

Centralizes phase switching logic and coordinates invoice processing workflows.
Integrates validation before processing and returns validation results on failure.
Delegates to specialized phase services based on invoice mode.
Does not contain phase-specific business logic or HTTP/FastAPI objects.

REFACTORED: Now includes invoice persistence with proper transaction handling.
"""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.constants import InvoiceMode
from app.schemas.invoice import InvoiceRequest, InvoiceResponse
from app.schemas.validation import ValidationResponse
from app.services.phase1.qr_service import QRService
from app.services.phase1.validator import Phase1Validator
from app.services.phase2.xml_generator import XMLGenerator
from app.services.phase2.crypto_service import CryptoService
from app.services.phase2.clearance_service import ClearanceService
from app.services.phase2.validator import Phase2Validator
from app.services.phase2.qr_service import Phase2QRService
from app.schemas.phase1 import QRCodeData
from app.schemas.phase2 import XMLData, ClearanceResponse as Phase2ClearanceResponse
from app.utils.time_utils import format_zatca_timestamp
from app.core.config import get_settings
from app.integrations.zatca.cert_manager import get_tenant_cert_paths
from app.schemas.auth import TenantContext
from app.models.invoice import Invoice, InvoiceStatus
from app.services.invoice_log_service import InvoiceLogService
from app.models.invoice_log import InvoiceLogStatus, InvoiceLog
from app.utils.webhook_trigger import schedule_webhook_trigger
from app.schemas.webhook import WebhookEvent
from app.services.zatca_policy_service import ZatcaPolicyService, ZatcaPolicyViolation

logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Orchestrates invoice processing workflows with centralized phase switching.
    
    REFACTORED: Now includes invoice persistence with proper transaction handling.
    """
    
    def __init__(
        self,
        db: Optional[Session] = None,
        tenant_context: Optional[TenantContext] = None,
        qr_service: QRService = None,
        phase1_validator: Phase1Validator = None,
        phase2_validator: Phase2Validator = None,
        xml_generator: XMLGenerator = None,
        crypto_service: CryptoService = None,
        clearance_service: ClearanceService = None,
        phase2_qr_service: Phase2QRService = None
    ):
        """
        Initializes invoice service with phase-specific services.
        
        Args:
            db: Database session (optional, required for persistence methods)
            tenant_context: Tenant context (optional, required for persistence methods)
            qr_service: QR code generation service for Phase-1
            phase1_validator: Phase-1 validation service
            phase2_validator: Phase-2 validation service
            xml_generator: XML generation service for Phase-2
            crypto_service: Cryptographic signing service for Phase-2
            clearance_service: Clearance service for Phase-2
            phase2_qr_service: QR code generation service for Phase-2
        """
        self.db = db
        self.tenant_context = tenant_context
        self.qr_service = qr_service or QRService()
        self.phase1_validator = phase1_validator or Phase1Validator()
        self.phase2_validator = phase2_validator or Phase2Validator()
        self.xml_generator = xml_generator or XMLGenerator()
        self.crypto_service = crypto_service or CryptoService()
        self.clearance_service = clearance_service or ClearanceService()
        self.phase2_qr_service = phase2_qr_service or Phase2QRService()
        self.policy_service = ZatcaPolicyService()
        # Note: audit_service removed - audit logging is handled by middleware
    
    async def process_invoice(
        self, 
        request: InvoiceRequest,
        tenant_context: Optional[TenantContext] = None
    ) -> InvoiceResponse:
        """
        Processes an invoice according to the specified mode.
        
        Execution flow:
        1. Run phase-specific validation
        2. If validation fails, return validation result immediately
        3. If validation passes, proceed with normal processing
        
        NOTE: This method does NOT persist invoice to database.
        Use process_invoice_with_persistence() for full persistence support.
        
        Args:
            request: Invoice processing request
            tenant_context: Tenant context (optional, for backward compatibility)
            
        Returns:
            Invoice processing response (with validation results if validation failed)
            
        Raises:
            ValueError: If unsupported invoice mode
        """
        logger.info(f"Processing invoice {request.invoice_number} in {request.mode} mode")
        
        if request.mode == InvoiceMode.PHASE_1:
            return await self._process_phase1(request)
        elif request.mode == InvoiceMode.PHASE_2:
            return await self._process_phase2(request, tenant_context)
        else:
            raise ValueError(f"Unsupported invoice mode: {request.mode}")
    
    async def process_invoice_with_persistence(
        self,
        request: InvoiceRequest,
        db: Session,
        tenant_context: TenantContext
    ) -> InvoiceResponse:
        """
        Processes an invoice with full persistence support.
        
        REFACTORED: This is the new enterprise-grade method that:
        1. Checks for duplicate invoices (idempotency)
        2. Persists invoice BEFORE ZATCA processing
        3. Updates invoice status during processing
        4. Ensures InvoiceLog is always written (success and failure)
        5. Handles errors and marks invoice as FAILED
        
        Execution flow:
        1. Check idempotency (tenant_id + invoice_number uniqueness)
        2. Create invoice record with status CREATED
        3. Run phase-specific validation
        4. If validation fails, update invoice status and return
        5. Update invoice status to PROCESSING
        6. Process invoice (Phase-1 or Phase-2)
        7. Update invoice with results (status, UUID, hash, XML, ZATCA response)
        8. Create InvoiceLog entry
        9. Return response
        
        Args:
            request: Invoice processing request
            db: Database session
            tenant_context: Tenant context (required for persistence)
            
        Returns:
            Invoice processing response
            
        Raises:
            ValueError: If duplicate invoice detected or unsupported invoice mode
        """
        if not db or not tenant_context:
            raise ValueError("Database session and tenant context are required for persistence")
        
        logger.info(
            f"Processing invoice with persistence: invoice_number={request.invoice_number}, "
            f"tenant_id={tenant_context.tenant_id}, mode={request.mode}"
        )
        
        # Step 1: Check idempotency and create/get invoice
        invoice = self._create_or_get_invoice(db, tenant_context, request)
        
        if invoice.status in [InvoiceStatus.CLEARED, InvoiceStatus.PROCESSING]:
            # Invoice already processed or currently processing
            logger.warning(
                f"Duplicate invoice submission detected: invoice_number={request.invoice_number}, "
                f"tenant_id={tenant_context.tenant_id}, current_status={invoice.status}"
            )
            raise ValueError(
                f"Invoice {request.invoice_number} already exists with status {invoice.status.value}. "
                f"Duplicate submissions are not allowed."
            )
        
        # Step 2: Update invoice status to PROCESSING
        self._update_invoice_status(db, invoice.id, InvoiceStatus.PROCESSING)
        
        # Step 3: Process invoice (with error handling)
        try:
            result = await self.process_invoice(request, tenant_context)
            
            # Step 4: Update invoice with results
            self._update_invoice_after_processing(
                db, invoice.id, result, request
            )
            
            # Step 5: Create InvoiceLog entry (always, even on failure)
            self._create_invoice_log(
                db, tenant_context, request, result, invoice.id
            )
            
            return result
            
        except Exception as e:
            # Step 6: Handle errors - mark invoice as FAILED
            error_message = str(e)
            logger.error(
                f"Invoice processing failed: invoice_number={request.invoice_number}, "
                f"tenant_id={tenant_context.tenant_id}, error={error_message}",
                exc_info=True
            )
            
            self._update_invoice_status(
                db, invoice.id, InvoiceStatus.FAILED, error_message=error_message
            )
            
            # Step 7: Create InvoiceLog entry for failure
            self._create_invoice_log(
                db, tenant_context, request, None, invoice.id, error_message=error_message
            )
            
            # Re-raise the exception
            raise
    
    async def retry_invoice(
        self,
        db: Session,
        invoice_id: int,
        tenant_context: TenantContext
    ) -> InvoiceResponse:
        """
        Retries processing a FAILED or REJECTED invoice.
        
        CRITICAL RULES:
        1. Only invoices with status FAILED or REJECTED can be retried
        2. CLEARED invoices must NOT be retried (raises ValueError)
        3. Tenant isolation is enforced (invoice must belong to tenant)
        4. Invoice master record is reused (NO new invoice row)
        5. Status flow: FAILED/REJECTED → PROCESSING → CLEARED/REJECTED/FAILED
        6. Creates audit log entry with action="RETRY"
        7. Reuses existing invoice processing logic
        
        Args:
            db: Database session
            invoice_id: Invoice ID to retry
            tenant_context: Tenant context (required for tenant isolation)
            
        Returns:
            Invoice processing response
            
        Raises:
            ValueError: If invoice not found, doesn't belong to tenant, or status invalid
        """
        if not db or not tenant_context:
            raise ValueError("Database session and tenant context are required for retry")
        
        logger.info(
            f"Retrying invoice: invoice_id={invoice_id}, tenant_id={tenant_context.tenant_id}"
        )
        
        # Step 1: Get invoice with tenant isolation
        invoice = db.query(Invoice).filter(
            Invoice.id == invoice_id,
            Invoice.tenant_id == tenant_context.tenant_id  # CRITICAL: Tenant isolation
        ).first()
        
        if not invoice:
            logger.warning(
                f"Invoice not found or access denied: invoice_id={invoice_id}, "
                f"tenant_id={tenant_context.tenant_id}"
            )
            raise ValueError(f"Invoice {invoice_id} not found or access denied")
        
        # Step 2: Validate status (only FAILED or REJECTED can be retried)
        if invoice.status == InvoiceStatus.CLEARED:
            logger.warning(
                f"Cannot retry CLEARED invoice: invoice_id={invoice_id}, "
                f"invoice_number={invoice.invoice_number}"
            )
            raise ValueError(
                f"Cannot retry invoice {invoice.invoice_number}: "
                f"Status is CLEARED. Only FAILED or REJECTED invoices can be retried."
            )
        
        if invoice.status not in [InvoiceStatus.FAILED, InvoiceStatus.REJECTED]:
            logger.warning(
                f"Cannot retry invoice with status {invoice.status.value}: "
                f"invoice_id={invoice_id}, invoice_number={invoice.invoice_number}"
            )
            raise ValueError(
                f"Cannot retry invoice {invoice.invoice_number}: "
                f"Status is {invoice.status.value}. Only FAILED or REJECTED invoices can be retried."
            )
        
        # Step 3: Get original request from most recent InvoiceLog
        invoice_log = db.query(InvoiceLog).filter(
            InvoiceLog.tenant_id == tenant_context.tenant_id,
            InvoiceLog.invoice_number == invoice.invoice_number
        ).order_by(InvoiceLog.created_at.desc()).first()
        
        if not invoice_log or not invoice_log.request_payload:
            logger.error(
                f"Cannot retry invoice: original request payload not found in logs. "
                f"invoice_id={invoice_id}, invoice_number={invoice.invoice_number}"
            )
            raise ValueError(
                f"Cannot retry invoice {invoice.invoice_number}: "
                f"Original request payload not found in audit logs."
            )
        
        # Step 4: Reconstruct InvoiceRequest from stored payload
        try:
            request_dict = invoice_log.request_payload
            # Ensure mode and environment are properly set from invoice
            request_dict["mode"] = invoice.phase.value
            request_dict["environment"] = invoice.environment.value
            request = InvoiceRequest(**request_dict)
        except Exception as e:
            logger.error(
                f"Failed to reconstruct InvoiceRequest from stored payload: "
                f"invoice_id={invoice_id}, error={str(e)}",
                exc_info=True
            )
            raise ValueError(
                f"Cannot retry invoice {invoice.invoice_number}: "
                f"Failed to reconstruct request from stored payload: {str(e)}"
            )
        
        # Step 5: Store previous status for audit log
        previous_status = invoice.status.value
        
        # Step 6: Update invoice status to PROCESSING and clear error_message
        self._update_invoice_status(
            db, invoice.id, InvoiceStatus.PROCESSING, error_message=None
        )
        
        # Step 6.5: Trigger retry_started webhook (after commit)
        if self.tenant_context:
            self._trigger_retry_webhook(invoice, "retry_started")
        
        # Step 7: Create RETRY audit log entry
        try:
            log_service = InvoiceLogService(db, tenant_context)
            log_service.create_log(
                invoice_number=invoice.invoice_number,
                environment=invoice.environment.value,
                status=InvoiceLogStatus.SUBMITTED,
                request_payload=request.model_dump(),
                action="RETRY",
                previous_status=previous_status
            )
            logger.info(
                f"Created RETRY audit log: invoice_id={invoice_id}, "
                f"invoice_number={invoice.invoice_number}, previous_status={previous_status}"
            )
        except Exception as e:
            # Log error but don't fail retry
            logger.error(
                f"Failed to create RETRY audit log: invoice_id={invoice_id}, error={str(e)}",
                exc_info=True
            )
        
        # Step 8: Process invoice (reuse existing logic)
        try:
            result = await self.process_invoice(request, tenant_context)
            
            # Step 9: Update invoice with results
            self._update_invoice_after_processing(
                db, invoice.id, result, request
            )
            
            # Step 10: Create final InvoiceLog entry (processing result)
            self._create_invoice_log(
                db, tenant_context, request, result, invoice.id
            )
            
            logger.info(
                f"Invoice retry completed successfully: invoice_id={invoice_id}, "
                f"invoice_number={invoice.invoice_number}, new_status={invoice.status.value}"
            )
            
            # Trigger retry_completed webhook (after commit)
            if self.tenant_context:
                self._trigger_retry_webhook(invoice, "retry_completed")
            
            return result
            
        except Exception as e:
            # Step 11: Handle errors - mark invoice as FAILED
            error_message = str(e)
            logger.error(
                f"Invoice retry failed: invoice_id={invoice_id}, "
                f"invoice_number={invoice.invoice_number}, error={error_message}",
                exc_info=True
            )
            
            self._update_invoice_status(
                db, invoice.id, InvoiceStatus.FAILED, error_message=error_message
            )
            
            # Step 12: Create InvoiceLog entry for failure
            self._create_invoice_log(
                db, tenant_context, request, None, invoice.id, error_message=error_message
            )
            
            # Re-raise the exception
            raise
    
    async def _process_phase1(self, request: InvoiceRequest) -> InvoiceResponse:
        """Processes Phase-1 invoice with integrated validation."""
        validation_result = await self.phase1_validator.validate(request)
        
        if validation_result.status == "FAIL":
            logger.warning(f"Phase-1 validation failed for invoice {request.invoice_number}")
            return InvoiceResponse(
                success=False,
                invoice_number=request.invoice_number,
                mode=request.mode,
                environment=request.environment,
                processed_at=datetime.now(),
                errors=[issue.message for issue in validation_result.issues if issue.severity == "error"],
                validation_result=validation_result
            )
        
        logger.info(f"Phase-1 validation passed for invoice {request.invoice_number}, generating QR code")
        
        # Generate QR code - wrap in try/except to prevent crashes if dependencies missing
        qr_code_data = None
        try:
            qr_data = self.qr_service.generate(
                seller_name=request.seller_name,
                seller_tax_number=request.seller_tax_number,
                invoice_date=request.invoice_date,
                invoice_total=request.total_amount,
                invoice_tax_amount=request.total_tax_amount
            )
            
            qr_code_data = QRCodeData(
                seller_name=request.seller_name,
                seller_tax_number=request.seller_tax_number,
                invoice_date=format_zatca_timestamp(request.invoice_date),
                invoice_total=f"{request.total_amount:.2f}",
                invoice_tax_amount=f"{request.total_tax_amount:.2f}",
                qr_code_base64=qr_data["qr_code_base64"]
            )
        except Exception as e:
            logger.warning(f"QR code generation failed for invoice {request.invoice_number}: {e}. Continuing without QR code.")
            # QR code is optional for Phase-1 - invoice can still succeed
            qr_code_data = None
        
        # Audit logging is handled by middleware, not in service layer
        
        # Build QR code data even if QR generation failed (QR is optional)
        if not qr_code_data:
            qr_code_data = QRCodeData(
                seller_name=request.seller_name,
                seller_tax_number=request.seller_tax_number,
                invoice_date=format_zatca_timestamp(request.invoice_date),
                invoice_total=f"{request.total_amount:.2f}",
                invoice_tax_amount=f"{request.total_tax_amount:.2f}",
                qr_code_base64=""  # Empty QR code if generation failed
            )
        
        return InvoiceResponse(
            success=True,
            invoice_number=request.invoice_number,
            mode=request.mode,
            environment=request.environment,
            qr_code_data=qr_code_data,
            processed_at=datetime.now()
        )
    
    async def _process_phase2(
        self, 
        request: InvoiceRequest,
        tenant_context: Optional[TenantContext] = None
    ) -> InvoiceResponse:
        """
        Processes Phase-2 invoice with integrated validation.
        
        Args:
            request: Invoice processing request
            tenant_context: Optional tenant context (for tenant-aware certificate/environment handling)
            
        Returns:
            Invoice processing response
        """
        # Get settings once at the beginning (avoid shadowing get_settings function)
        settings = get_settings()
        
        # TEMPORARY: Verification log for Phase-2 flow validation
        if settings.debug:
            logger.info(f"[PHASE2_VERIFY] Starting Phase-2 flow for invoice {request.invoice_number}")
        
        # CRITICAL: Override payload totals with system-calculated totals (system is source of truth)
        # Payload totals are NON-AUTHORITATIVE - we compute from line items
        calculated_totals = self._calculate_totals_from_lines(request)
        request.total_tax_exclusive = calculated_totals["tax_exclusive"]
        request.total_tax_amount = calculated_totals["tax_amount"]
        request.total_amount = calculated_totals["total"]
        
        if settings.debug:
            logger.info(
                f"[PHASE2_VERIFY] Overrode payload totals with calculated values: "
                f"tax_exclusive={request.total_tax_exclusive:.2f}, "
                f"tax_amount={request.total_tax_amount:.2f}, "
                f"total={request.total_amount:.2f}"
            )
        
        validation_result = await self.phase2_validator.validate(request)
        
        if validation_result.status == "FAIL":
            logger.warning(f"Phase-2 validation failed for invoice {request.invoice_number}")
            
            # TEMPORARY: Verification log for Phase-2 flow validation
            if settings.debug:
                logger.info(f"[PHASE2_VERIFY] Phase-2 flow early exit: validation failed for invoice {request.invoice_number}")
            
            return InvoiceResponse(
                success=False,
                invoice_number=request.invoice_number,
                mode=request.mode,
                environment=request.environment,
                processed_at=datetime.now(),
                errors=[issue.message for issue in validation_result.issues if issue.severity == "error"],
                validation_result=validation_result
            )
        
        logger.info(f"Phase-2 validation passed for invoice {request.invoice_number}, generating XML and submitting to ZATCA")
        
        # CRITICAL: Enforce ZATCA policy before processing
        try:
            # Validate clearance is allowed for this environment/invoice type
            self.policy_service.validate_clearance_allowed(
                environment=request.environment,
                invoice_type=request.invoice_type
            )
        except ZatcaPolicyViolation as e:
            logger.error(
                f"ZATCA policy violation for invoice {request.invoice_number}: {e.message}",
                extra={
                    "invoice_number": request.invoice_number,
                    "environment": request.environment.value,
                    "invoice_type": request.invoice_type,
                    "error_code": e.error_code
                }
            )
            raise ValueError(
                f"ZATCA_POLICY_VIOLATION: {e.message}"
            ) from e
        
        try:
            # Step 1: Resolve per-tenant signing assets (ZATCA audit: no global cert for Phase-2 when tenant exists)
            if tenant_context:
                paths = get_tenant_cert_paths(
                    tenant_context.tenant_id,
                    request.environment.value
                )
                phase2_crypto = CryptoService(
                    private_key_path=str(paths["key_path"]),
                    certificate_path=str(paths["cert_path"]),
                )
            else:
                phase2_crypto = self.crypto_service

            # Step 2: Generate XML
            xml_content = self.xml_generator.generate(request)

            # Step 3: Compute XML hash (of unsigned XML)
            xml_hash = phase2_crypto.compute_xml_hash(xml_content)

            # Step 4: Sign XML — REAL signing only; no placeholder may reach clearance
            zatca_env = settings.zatca_environment
            signed_xml, digital_signature = await phase2_crypto.sign(
                xml_content,
                environment=zatca_env,
                allow_placeholder=False,
            )

            # CRITICAL: Safety guards before clearance submission
            self._validate_pre_clearance_safety(request, signed_xml, digital_signature, xml_content)

            # Step 5: Compute hash of SIGNED XML (for clearance submission)
            signed_xml_hash = phase2_crypto.compute_xml_hash(signed_xml)
            
            # Step 6: Generate Phase-2 QR code (includes XML hash and signature)
            # QR code generation is optional - will use clearance QR from ZATCA if available
            try:
                qr_data = self.phase2_qr_service.generate(
                    seller_name=request.seller_name,
                    seller_tax_number=request.seller_tax_number,
                    invoice_date=request.invoice_date,
                    invoice_total=request.total_amount,
                    invoice_tax_amount=request.total_tax_amount,
                    xml_hash=signed_xml_hash,  # Use signed XML hash
                    digital_signature=digital_signature or ""
                )
                generated_qr = qr_data.get("qr_code_base64", "")
            except Exception as e:
                logger.warning(f"QR code generation failed, will use clearance QR: {e}")
                generated_qr = ""
            
            # Step 7: Prepare XML data
            # CRITICAL: Ensure all fields are populated (no empty strings for Phase-2)
            xml_data = XMLData(
                xml_content=xml_content,
                xml_hash=xml_hash,  # Hash of unsigned XML (will be updated to signed hash)
                signed_xml=signed_xml,  # Must be non-empty
                digital_signature=digital_signature  # Must be non-empty (validated in safety guards)
            )
            
            # Step 7: Submit to ZATCA for clearance (MUST use signed XML)
            # CRITICAL: Use tenant environment, not global config
            tenant_env = tenant_context.environment if tenant_context else settings.zatca_environment
            
            # Create tenant-aware clearance service if tenant context available
            if tenant_context:
                from app.services.phase2.clearance_service import ClearanceService
                clearance_service = ClearanceService(environment=tenant_env)
            else:
                clearance_service = self.clearance_service
            
            clearance = await clearance_service.submit_clearance(
                signed_xml=signed_xml,  # CRITICAL: Must use signed XML, not unsigned
                invoice_uuid=request.uuid or ""
            )
            
            # Step 9: Use QR code from clearance if provided, otherwise use generated one
            # CRITICAL: Do NOT include local QR if clearance QR exists (ZATCA requirement)
            qr_code_final = clearance.get("qr_code") or generated_qr
            
            # Step 10: Automatic Reporting after Successful Clearance
            # If clearance status is CLEARED, automatically report invoice to ZATCA
            reporting_result = None
            reporting_error = None
            clearance_status = clearance.get("status", "REJECTED")
            
            if clearance_status == "CLEARED":
                # Get invoice UUID for reporting (use clearance UUID if available, otherwise request UUID)
                invoice_uuid_for_reporting = clearance.get("uuid") or request.uuid or ""
                
                if invoice_uuid_for_reporting:
                    # CRITICAL: Validate that reporting is allowed after clearance
                    # This checks if automatic reporting (clearance + reporting) is allowed
                    try:
                        self.policy_service.validate_clearance_and_reporting_allowed(
                            environment=request.environment,
                            invoice_type=request.invoice_type
                        )
                    except ZatcaPolicyViolation as e:
                        # In production, automatic reporting after clearance is NOT allowed
                        # Log warning but do NOT fail the invoice (clearance succeeded)
                        logger.warning(
                            f"Automatic reporting blocked by ZATCA policy for invoice {request.invoice_number}: {e.message}. "
                            f"Clearance status remains CLEARED.",
                            extra={
                                "invoice_number": request.invoice_number,
                                "environment": request.environment.value,
                                "invoice_type": request.invoice_type,
                                "error_code": e.error_code,
                                "clearance_status": clearance_status
                            }
                        )
                        # Skip reporting - invoice is still cleared
                        invoice_uuid_for_reporting = None
                    
                    if invoice_uuid_for_reporting:
                        try:
                            logger.info(
                                f"Automatically reporting invoice {request.invoice_number} to ZATCA "
                                f"(UUID: {invoice_uuid_for_reporting}) after successful clearance"
                            )
                            
                            # Call reporting API with clearance status for headers
                            reporting_result = await clearance_service.report(
                                invoice_uuid=invoice_uuid_for_reporting,
                                clearance_status=clearance_status
                            )
                        
                            logger.info(
                                f"Successfully reported invoice {request.invoice_number} to ZATCA. "
                                f"Reporting status: {reporting_result.get('status', 'UNKNOWN')}"
                            )
                        except ZatcaPolicyViolation as e:
                            # Policy violation during reporting (should not happen if check above passed)
                            # Log error but do NOT fail invoice
                            reporting_error = f"ZATCA_POLICY_VIOLATION: {e.message}"
                            logger.warning(
                                f"Reporting blocked by ZATCA policy for invoice {request.invoice_number}: {e.message}. "
                                f"Clearance status remains CLEARED.",
                                extra={
                                    "invoice_number": request.invoice_number,
                                    "invoice_uuid": invoice_uuid_for_reporting,
                                    "clearance_status": clearance_status,
                                    "error_code": e.error_code
                                }
                            )
                        except Exception as e:
                            # CRITICAL: Do NOT fail invoice if reporting fails
                            # Log warning and continue with clearance success
                            reporting_error = str(e)
                            logger.warning(
                                f"Reporting failed for invoice {request.invoice_number} after successful clearance: {e}. "
                                f"Clearance status remains CLEARED. Error: {reporting_error}",
                                extra={
                                    "invoice_number": request.invoice_number,
                                    "invoice_uuid": invoice_uuid_for_reporting,
                                    "clearance_status": clearance_status,
                                    "reporting_error": reporting_error
                                },
                                exc_info=True
                            )
                    else:
                        if invoice_uuid_for_reporting is None:
                            logger.info(
                                f"Skipping automatic reporting for invoice {request.invoice_number}: "
                                f"Policy does not allow mixed flow (clearance + reporting) in {request.environment.value}"
                            )
                        else:
                            logger.warning(
                                f"Cannot report invoice {request.invoice_number}: No UUID available "
                                f"(clearance UUID: {clearance.get('uuid')}, request UUID: {request.uuid})"
                            )
            
            # Step 10: Ensure response contract includes all required fields
            # Include reporting status from either reporting API call or clearance response
            reporting_status = None
            if reporting_result:
                reporting_status = reporting_result.get("status")
            elif clearance.get("reporting_status"):
                # Fallback to reporting_status from clearance response if available
                reporting_status = clearance.get("reporting_status")
            
            clearance_response = Phase2ClearanceResponse(
                clearance_status=clearance_status,
                clearance_uuid=clearance.get("uuid", request.uuid or ""),
                qr_code=qr_code_final or "",  # Ensure not None
                reporting_status=reporting_status
            )
            
            # CRITICAL: Update xml_data with signed XML hash for response
            xml_data.xml_hash = signed_xml_hash  # Use signed XML hash in response
            
            # Extract ZATCA response code from clearance response
            zatca_response_code = None
            if clearance.get("error"):
                # Try to extract error code from error message
                from app.integrations.zatca.error_catalog import extract_error_code_from_message
                zatca_response_code = extract_error_code_from_message(clearance.get("error", ""))
            
            # Prepare response with both clearance and reporting results
            response_data = {
                "success": True,
                "invoice_number": request.invoice_number,
                "mode": request.mode,
                "environment": request.environment,
                "xml_data": xml_data,
                "clearance": clearance_response,
                "processed_at": datetime.now()
            }
            
            # Add reporting result to response if available
            if reporting_result:
                response_data["reporting"] = {
                    "status": reporting_result.get("status", "UNKNOWN"),
                    "message": reporting_result.get("message", ""),
                    "reported_at": datetime.now().isoformat()
                }
            elif reporting_error:
                # Include reporting error in response (non-blocking)
                response_data["reporting"] = {
                    "status": "FAILED",
                    "error": reporting_error,
                    "note": "Reporting failed but clearance was successful. Invoice is cleared."
                }
            
            # Audit logging is handled by middleware, not in service layer
            
            # TEMPORARY: Verification log for Phase-2 flow validation
            if settings.debug:
                logger.info(
                    f"[PHASE2_VERIFY] Phase-2 flow completed successfully for invoice {request.invoice_number}, "
                    f"clearance status: {clearance_response.clearance_status}, "
                    f"reporting status: {reporting_status}"
                )
            
            return InvoiceResponse(**response_data)
        except Exception as e:
            logger.error(f"Phase-2 processing error for invoice {request.invoice_number}: {e}")
            
            # TEMPORARY: Verification log for Phase-2 flow validation
            if settings.debug:
                logger.info(f"[PHASE2_VERIFY] Phase-2 flow error for invoice {request.invoice_number}: {str(e)}")
            
            raise ValueError(f"Phase-2 processing failed: {str(e)}")
    
    def _create_or_get_invoice(
        self,
        db: Session,
        tenant_context: TenantContext,
        request: InvoiceRequest
    ) -> Invoice:
        """
        Creates a new invoice or returns existing one (idempotency check).
        
        CRITICAL: Enforces tenant_id + invoice_number uniqueness.
        If invoice already exists, returns existing invoice.
        
        Args:
            db: Database session
            tenant_context: Tenant context
            request: Invoice request
            
        Returns:
            Invoice instance (newly created or existing)
            
        Raises:
            ValueError: If duplicate invoice detected with conflicting status
        """
        # Check if invoice already exists
        existing_invoice = db.query(Invoice).filter(
            Invoice.tenant_id == tenant_context.tenant_id,
            Invoice.invoice_number == request.invoice_number
        ).first()
        
        if existing_invoice:
            logger.info(
                f"Invoice already exists: invoice_number={request.invoice_number}, "
                f"tenant_id={tenant_context.tenant_id}, status={existing_invoice.status}"
            )
            return existing_invoice
        
        # Create new invoice
        invoice = Invoice(
            tenant_id=tenant_context.tenant_id,
            invoice_number=request.invoice_number,
            phase=request.mode,
            status=InvoiceStatus.CREATED,
            environment=request.environment,
            total_amount=request.total_amount,
            tax_amount=request.total_tax_amount
        )
        
        try:
            db.add(invoice)
            db.commit()
            db.refresh(invoice)
            
            logger.info(
                f"Created invoice: id={invoice.id}, invoice_number={request.invoice_number}, "
                f"tenant_id={tenant_context.tenant_id}"
            )
            
            return invoice
            
        except IntegrityError as e:
            db.rollback()
            # Handle race condition: invoice was created by another request
            logger.warning(
                f"Race condition detected: invoice_number={request.invoice_number}, "
                f"tenant_id={tenant_context.tenant_id}"
            )
            # Retry: get the invoice that was just created
            existing_invoice = db.query(Invoice).filter(
                Invoice.tenant_id == tenant_context.tenant_id,
                Invoice.invoice_number == request.invoice_number
            ).first()
            
            if existing_invoice:
                return existing_invoice
            else:
                raise ValueError(f"Failed to create invoice: {str(e)}")
    
    def _update_invoice_status(
        self,
        db: Session,
        invoice_id: int,
        status: InvoiceStatus,
        error_message: Optional[str] = None
    ) -> None:
        """
        Updates invoice status.
        
        Args:
            db: Database session
            invoice_id: Invoice ID
            status: New status
            error_message: Optional error message (for FAILED status)
        """
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            logger.error(f"Invoice not found: id={invoice_id}")
            return
        
        invoice.status = status
        # Explicitly set error_message (clear if None, set if provided)
        invoice.error_message = error_message
        invoice.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(invoice)
        
        logger.info(f"Updated invoice status: id={invoice_id}, status={status.value}")
        
        # Trigger webhook after commit (if status is a webhook event)
        if self.tenant_context:
            self._trigger_status_webhook(invoice, status)
    
    def _update_invoice_after_processing(
        self,
        db: Session,
        invoice_id: int,
        result: InvoiceResponse,
        request: InvoiceRequest
    ) -> None:
        """
        Updates invoice with processing results.
        
        Args:
            db: Database session
            invoice_id: Invoice ID
            result: Processing result (dict or InvoiceResponse object)
            request: Original invoice request
        """
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            logger.error(f"Invoice not found: id={invoice_id}")
            return
        
        # Normalize access to result (handles both dict and object-based results)
        success = result.get("success") if isinstance(result, dict) else getattr(result, "success", False)
        errors = result.get("errors") if isinstance(result, dict) else getattr(result, "errors", None)
        clearance = result.get("clearance") if isinstance(result, dict) else getattr(result, "clearance", None)
        xml_data = result.get("xml_data") if isinstance(result, dict) else getattr(result, "xml_data", None)
        
        # Update status based on result
        if not success:
            invoice.status = InvoiceStatus.REJECTED
            if errors:
                error_list = errors if isinstance(errors, list) else [errors] if errors else []
                invoice.error_message = "; ".join(str(e) for e in error_list)
        else:
            # Determine status from clearance (Phase-2) or default to CLEARED (Phase-1)
            if clearance:
                clearance_status = (
                    clearance.clearance_status
                    if hasattr(clearance, 'clearance_status')
                    else clearance.get('clearance_status') if isinstance(clearance, dict) else None
                )
                if clearance_status == "CLEARED":
                    invoice.status = InvoiceStatus.CLEARED
                elif clearance_status == "REJECTED":
                    invoice.status = InvoiceStatus.REJECTED
                else:
                    invoice.status = InvoiceStatus.CLEARED  # Default for Phase-1
            else:
                invoice.status = InvoiceStatus.CLEARED  # Phase-1 invoices are always cleared
        
        # Update Phase-2 fields
        if xml_data:
            invoice.xml_content = (
                xml_data.signed_xml
                if hasattr(xml_data, 'signed_xml')
                else xml_data.get('signed_xml') if isinstance(xml_data, dict) else None
            )
            invoice.hash = (
                xml_data.xml_hash
                if hasattr(xml_data, 'xml_hash')
                else xml_data.get('xml_hash') if isinstance(xml_data, dict) else None
            )
        
        # Update UUID from clearance
        if clearance:
            uuid = (
                clearance.clearance_uuid
                if hasattr(clearance, 'clearance_uuid')
                else clearance.get('clearance_uuid') if isinstance(clearance, dict) else None
            )
            if uuid:
                invoice.uuid = uuid
        
        # Store ZATCA response (clearance + reporting)
        zatca_response = {}
        if clearance:
            zatca_response = {
                "clearance_status": (
                    clearance.clearance_status
                    if hasattr(clearance, 'clearance_status')
                    else clearance.get('clearance_status') if isinstance(clearance, dict) else None
                ),
                "clearance_uuid": (
                    clearance.clearance_uuid
                    if hasattr(clearance, 'clearance_uuid')
                    else clearance.get('clearance_uuid') if isinstance(clearance, dict) else None
                ),
                "reporting_status": (
                    clearance.reporting_status
                    if hasattr(clearance, 'reporting_status')
                    else clearance.get('reporting_status') if isinstance(clearance, dict) else None
                )
            }
        
        # Store reporting response if available (from automatic reporting after clearance)
        reporting = result.get("reporting") if isinstance(result, dict) else getattr(result, "reporting", None)
        if reporting:
            if not zatca_response:
                zatca_response = {}
            zatca_response["reporting_response"] = (
                reporting if isinstance(reporting, dict) else reporting.model_dump() if hasattr(reporting, 'model_dump') else {}
            )
            # Update reporting_status from reporting response if not already set
            if not zatca_response.get("reporting_status"):
                reporting_status = (
                    reporting.get("status")
                    if isinstance(reporting, dict)
                    else getattr(reporting, "status", None) if reporting else None
                )
                if reporting_status:
                    zatca_response["reporting_status"] = reporting_status
        
        invoice.zatca_response = zatca_response if zatca_response else None
        
        invoice.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(invoice)
        
        logger.info(
            f"Updated invoice after processing: id={invoice_id}, status={invoice.status.value}"
        )
        
        # Trigger webhook after commit (if status is a webhook event)
        if self.tenant_context:
            self._trigger_status_webhook(invoice)
    
    def _create_invoice_log(
        self,
        db: Session,
        tenant_context: TenantContext,
        request: InvoiceRequest,
        result: Optional[InvoiceResponse],
        invoice_id: int,
        error_message: Optional[str] = None
    ) -> None:
        """
        Creates InvoiceLog entry (always, even on failure).
        
        CRITICAL: This ensures we always have a log entry for audit purposes.
        
        Args:
            db: Database session
            tenant_context: Tenant context
            request: Invoice request
            result: Processing result (None if failed)
            invoice_id: Invoice ID (for linking)
            error_message: Error message (if processing failed)
        """
        try:
            log_service = InvoiceLogService(db, tenant_context)
            
            # Normalize access to result (handles both dict and object-based results)
            result_success = None
            result_clearance = None
            result_xml_data = None
            if result:
                result_success = result.get("success") if isinstance(result, dict) else getattr(result, "success", None)
                result_clearance = result.get("clearance") if isinstance(result, dict) else getattr(result, "clearance", None)
                result_xml_data = result.get("xml_data") if isinstance(result, dict) else getattr(result, "xml_data", None)
            
            # Determine status
            if error_message or (result and not result_success):
                log_status = InvoiceLogStatus.ERROR
                zatca_response_code = None
            elif result and result_clearance:
                clearance = result_clearance
                clearance_status = (
                    clearance.clearance_status
                    if hasattr(clearance, 'clearance_status')
                    else clearance.get('clearance_status') if isinstance(clearance, dict) else None
                )
                if clearance_status == "CLEARED":
                    log_status = InvoiceLogStatus.CLEARED
                elif clearance_status == "REJECTED":
                    log_status = InvoiceLogStatus.REJECTED
                else:
                    log_status = InvoiceLogStatus.SUBMITTED
            else:
                log_status = InvoiceLogStatus.SUBMITTED
            
            # Extract UUID and hash
            uuid = None
            hash_value = None
            if result:
                if result_clearance:
                    clearance = result_clearance
                    uuid = (
                        clearance.clearance_uuid
                        if hasattr(clearance, 'clearance_uuid')
                        else clearance.get('clearance_uuid') if isinstance(clearance, dict) else None
                    )
                if result_xml_data:
                    xml_data = result_xml_data
                    hash_value = (
                        xml_data.xml_hash
                        if hasattr(xml_data, 'xml_hash')
                        else xml_data.get('xml_hash') if isinstance(xml_data, dict) else None
                    )
            
            # Prepare artifacts
            request_payload = request.model_dump() if request else None
            generated_xml = None
            zatca_response = None
            
            if result and result_xml_data:
                xml_data = result_xml_data
                generated_xml = (
                    xml_data.signed_xml
                    if hasattr(xml_data, 'signed_xml')
                    else xml_data.get('signed_xml') if isinstance(xml_data, dict) else None
                )
            
            if result and result_clearance:
                clearance = result_clearance
                zatca_response = {
                    "clearance_status": (
                        clearance.clearance_status
                        if hasattr(clearance, 'clearance_status')
                        else clearance.get('clearance_status') if isinstance(clearance, dict) else None
                    ),
                    "clearance_uuid": (
                        clearance.clearance_uuid
                        if hasattr(clearance, 'clearance_uuid')
                        else clearance.get('clearance_uuid') if isinstance(clearance, dict) else None
                    ),
                    "reporting_status": (
                        clearance.reporting_status
                        if hasattr(clearance, 'reporting_status')
                        else clearance.get('reporting_status') if isinstance(clearance, dict) else None
                    )
                }
            
            # Create log entry
            log_service.create_log(
                invoice_number=request.invoice_number,
                uuid=uuid,
                hash=hash_value,
                environment=request.environment.value if hasattr(request.environment, 'value') else str(request.environment),
                status=log_status,
                zatca_response_code=error_message if error_message else None,
                request_payload=request_payload,
                generated_xml=generated_xml,
                zatca_response=zatca_response,
                submitted_at=datetime.utcnow() if result else None,
                cleared_at=datetime.utcnow() if log_status == InvoiceLogStatus.CLEARED else None
            )
            
            logger.info(
                f"Created invoice log: invoice_number={request.invoice_number}, "
                f"status={log_status.value}, invoice_id={invoice_id}"
            )
            
        except Exception as e:
            # Log error but don't fail the invoice processing
            logger.error(
                f"Failed to create invoice log: invoice_number={request.invoice_number}, "
                f"invoice_id={invoice_id}, error={str(e)}",
                exc_info=True
            )
    
    def _calculate_totals_from_lines(self, request: InvoiceRequest) -> dict[str, float]:
        """
        Calculates invoice totals from line items (system is source of truth).
        
        CRITICAL: Payload totals are NON-AUTHORITATIVE.
        Always compute totals internally from line taxable amounts.
        
        Returns:
            Dictionary with tax_exclusive, tax_amount, and total
        """
        if not request.line_items:
            return {
                "tax_exclusive": 0.0,
                "tax_amount": 0.0,
                "total": 0.0
            }
        
        # TaxExclusiveAmount = SUM(all line_taxable) where line_taxable = (qty × price) - discount
        calculated_tax_exclusive = sum(item.taxable_amount for item in request.line_items)
        
        # TaxTotal = SUM(all line_vat) where line_vat = line_taxable × tax_rate
        calculated_tax_amount = sum(item.tax_amount for item in request.line_items)
        
        # TaxInclusiveAmount = TaxExclusiveAmount + TaxTotal
        calculated_total = calculated_tax_exclusive + calculated_tax_amount
        
        return {
            "tax_exclusive": round(calculated_tax_exclusive, 2),
            "tax_amount": round(calculated_tax_amount, 2),
            "total": round(calculated_total, 2)
        }
    
    def _validate_pre_clearance_safety(
        self,
        request: InvoiceRequest,
        signed_xml: str,
        digital_signature: str,
        xml_content: str
    ) -> None:
        """
        Safety guards before clearance submission (non-blocking, fast validation).
        
        Validates:
        - All tax percent values are identical (15.00)
        - Digital signature is not empty
        - VAT math consistency
        
        Raises:
            ValueError: If any safety check fails
        """
        from xml.etree import ElementTree as ET
        
        # Guard 1: Assert digital_signature is not empty (fast string check)
        if not digital_signature or digital_signature.strip() == "":
            raise ValueError(
                "CRITICAL: digital_signature is empty. ZATCA Phase-2 requires non-empty digital signature. "
                "Ensure signing keys are configured and XML signing succeeds."
            )
        
        # Guard 2: Assert ALL cbc:Percent values are identical (fast XML parsing)
        # Note: ET.fromstring is fast and in-memory, won't block event loop
        try:
            root = ET.fromstring(xml_content)
            percent_values = []
            
            # Find all Percent elements (fast iteration)
            for elem in root.iter():
                if elem.tag.endswith("Percent") or "Percent" in elem.tag:
                    if elem.text:
                        try:
                            percent_value = float(elem.text.strip())
                            percent_values.append(percent_value)
                        except ValueError:
                            pass
            
            if percent_values:
                # Check if all values are identical
                unique_percents = set(percent_values)
                if len(unique_percents) > 1:
                    raise ValueError(
                        f"CRITICAL: Tax percent inconsistency detected. Found values: {sorted(unique_percents)}. "
                        f"ZATCA requires ALL cbc:Percent values to be identical (15.00). "
                        f"This violation will cause clearance REJECTION."
                    )
                
                # Check if standard VAT rate is 15.00
                if 15.0 not in unique_percents and 15.00 not in unique_percents:
                    standard_rate = next(iter(unique_percents))
                    if abs(standard_rate - 15.0) > 0.01:  # Allow small floating point tolerance
                        raise ValueError(
                            f"CRITICAL: Standard VAT rate must be 15.00, found {standard_rate}. "
                            f"This violation will cause clearance REJECTION."
                        )
        except ET.ParseError as e:
            logger.warning(f"Could not parse XML for tax percent validation: {e}")
        
        # Guard 3: Assert AllowanceCharge exists for lines with discount
        try:
            root = ET.fromstring(xml_content)
            for idx, item in enumerate(request.line_items, start=1):
                discount_amount = item.discount or 0.0
                if discount_amount > 0:
                    # Find the InvoiceLine element
                    invoice_lines = root.findall(".//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}InvoiceLine")
                    if idx <= len(invoice_lines):
                        line_elem = invoice_lines[idx - 1]
                        # Check if AllowanceCharge exists
                        allowance_charges = line_elem.findall(".//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AllowanceCharge")
                        if not allowance_charges:
                            raise ValueError(
                                f"CRITICAL: Line {idx} has discount ({discount_amount:.2f}) but missing <cac:AllowanceCharge> element. "
                                f"ZATCA requires AllowanceCharge for discounted lines. This violation will cause clearance REJECTION."
                            )
                        # Validate ChargeIndicator is false
                        charge_indicator = allowance_charges[0].find(".//{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ChargeIndicator")
                        if charge_indicator is not None and charge_indicator.text.lower() != "false":
                            raise ValueError(
                                f"CRITICAL: Line {idx} AllowanceCharge ChargeIndicator must be 'false' for discounts. "
                                f"This violation will cause clearance REJECTION."
                            )
        except ET.ParseError as e:
            logger.warning(f"Could not parse XML for AllowanceCharge validation: {e}")
        
        # Guard 4: Assert VAT math consistency (computed from line values)
        # NOTE: request totals were already overridden with calculated values, so this is a sanity check
        tolerance = 0.01
        
        # Calculate totals from line items (line_taxable = qty × price - discount)
        calculated_line_taxable = sum(item.taxable_amount for item in request.line_items)
        calculated_total_tax = sum(item.tax_amount for item in request.line_items)
        calculated_total = calculated_line_taxable + calculated_total_tax
        
        # These should match since totals were overridden, but verify internal consistency
        if abs(calculated_total_tax - request.total_tax_amount) > tolerance:
            raise ValueError(
                f"CRITICAL: Internal VAT math inconsistency. "
                f"Sum of line taxes ({calculated_total_tax:.2f}) != total_tax_amount ({request.total_tax_amount:.2f}). "
                f"This should not happen after totals override. This violation will cause clearance REJECTION."
            )
        
        # TaxExclusiveAmount = SUM(all line_taxable) where line_taxable = (qty × price) - discount
        if abs(calculated_line_taxable - request.total_tax_exclusive) > tolerance:
            raise ValueError(
                f"CRITICAL: Internal tax exclusive amount inconsistency. "
                f"Sum of line taxable amounts ({calculated_line_taxable:.2f}) != total_tax_exclusive ({request.total_tax_exclusive:.2f}). "
                f"This should not happen after totals override. This violation will cause clearance REJECTION."
            )
        
        # TaxInclusiveAmount = TaxExclusive + TaxTotal
        if abs(calculated_total - request.total_amount) > tolerance:
            raise ValueError(
                f"CRITICAL: Internal total amount inconsistency. "
                f"Calculated total ({calculated_total:.2f}) != total_amount ({request.total_amount:.2f}). "
                f"This should not happen after totals override. This violation will cause clearance REJECTION."
            )
        
        # Guard 5: Validate TaxableAmount calculation in XML matches (qty × price) - discount
        try:
            root = ET.fromstring(xml_content)
            invoice_lines = root.findall(".//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}InvoiceLine")
            for idx, (line_elem, item) in enumerate(zip(invoice_lines, request.line_items), start=1):
                # Calculate expected taxable amount
                expected_taxable = item.taxable_amount
                
                # Find TaxableAmount in XML
                tax_subtotals = line_elem.findall(".//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxSubtotal")
                if tax_subtotals:
                    taxable_elem = tax_subtotals[0].find(".//{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxableAmount")
                    if taxable_elem is not None and taxable_elem.text:
                        try:
                            xml_taxable = float(taxable_elem.text.strip())
                            if abs(xml_taxable - expected_taxable) > tolerance:
                                raise ValueError(
                                    f"CRITICAL: Line {idx} TaxableAmount mismatch. "
                                    f"XML has {xml_taxable:.2f}, expected {(item.quantity * item.unit_price) - (item.discount or 0.0):.2f}. "
                                    f"This violation will cause clearance REJECTION."
                                )
                        except ValueError:
                            pass  # Skip if can't parse
        except ET.ParseError as e:
            logger.warning(f"Could not parse XML for TaxableAmount validation: {e}")
    
    def _trigger_status_webhook(self, invoice: Invoice, status: Optional[InvoiceStatus] = None) -> None:
        """
        Triggers webhook for invoice status change.
        
        Args:
            invoice: Invoice instance
            status: Optional status (if None, uses invoice.status)
        """
        if not self.tenant_context:
            return
        
        # Use provided status or invoice status
        invoice_status = status or invoice.status
        
        # Map invoice status to webhook event
        event_map = {
            InvoiceStatus.CLEARED: WebhookEvent.INVOICE_CLEARED,
            InvoiceStatus.REJECTED: WebhookEvent.INVOICE_REJECTED,
            InvoiceStatus.FAILED: WebhookEvent.INVOICE_FAILED,
        }
        
        event = event_map.get(invoice_status)
        if not event:
            return  # No webhook for this status
        
        # Build payload
        payload = {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "status": invoice_status.value,
            "phase": invoice.phase.value,
            "environment": invoice.environment.value,
            "total_amount": invoice.total_amount,
            "vat_amount": invoice.tax_amount,
        }
        
        # Add optional fields if available
        if invoice.uuid:
            payload["uuid"] = invoice.uuid
        if invoice.hash:
            payload["hash"] = invoice.hash
        
        # Schedule webhook trigger (fire-and-forget, after commit)
        schedule_webhook_trigger(self.tenant_context, event, payload)
    
    def _trigger_retry_webhook(self, invoice: Invoice, event_type: str) -> None:
        """
        Triggers webhook for retry events.
        
        Args:
            invoice: Invoice instance
            event_type: Either "retry_started" or "retry_completed"
        """
        if not self.tenant_context:
            return
        
        event_map = {
            "retry_started": WebhookEvent.INVOICE_RETRY_STARTED,
            "retry_completed": WebhookEvent.INVOICE_RETRY_COMPLETED,
        }
        
        event = event_map.get(event_type)
        if not event:
            return
        
        # Build payload
        payload = {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "status": invoice.status.value,
            "phase": invoice.phase.value,
            "environment": invoice.environment.value,
            "total_amount": invoice.total_amount,
            "vat_amount": invoice.tax_amount,
        }
        
        # Add optional fields if available
        if invoice.uuid:
            payload["uuid"] = invoice.uuid
        if invoice.hash:
            payload["hash"] = invoice.hash
        
        # Schedule webhook trigger (fire-and-forget, after commit)
        schedule_webhook_trigger(self.tenant_context, event, payload)
        
        logger.info("Pre-clearance safety guards passed: AllowanceCharge, tax consistency, digital signature, and VAT math validated")
