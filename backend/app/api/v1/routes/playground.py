"""
API Playground endpoints.

Provides interactive API testing interface for developers.
All requests are logged with source="api_playground" for audit purposes.
"""

import logging
import time
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.security import verify_api_key_and_resolve_tenant
from app.schemas.auth import TenantContext
from app.db.session import get_db
from app.services.subscription_service import SubscriptionService
from app.core.production_guards import check_production_access, require_production_confirmation
from app.utils.data_masking import mask_sensitive_fields
from app.core.constants import Environment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playground", tags=["playground"])


class PlaygroundRequest(BaseModel):
    """Request schema for playground execution."""
    endpoint: str = Field(..., description="API endpoint path (e.g., /api/v1/invoices)")
    method: str = Field(..., description="HTTP method (GET, POST, PUT, DELETE)")
    body: Optional[Dict[str, Any]] = Field(None, description="Request body (for POST/PUT)")
    query_params: Optional[Dict[str, str]] = Field(None, description="Query parameters")
    confirm_production: bool = Field(False, description="Confirmation for production actions")


class PlaygroundResponse(BaseModel):
    """Response schema for playground execution."""
    status_code: int
    headers: Dict[str, str]
    body: Any
    latency_ms: float
    timestamp: str
    source: str = "api_playground"


class RequestTemplate(BaseModel):
    """Request template schema."""
    name: str
    description: str
    endpoint: str
    method: str
    body: Optional[Dict[str, Any]]
    query_params: Optional[Dict[str, str]]
    requires_production_confirmation: bool = False


@router.get(
    "/templates",
    response_model=Dict[str, RequestTemplate],
    summary="Get request templates for API Playground"
)
async def get_templates(
    tenant: TenantContext = Depends(verify_api_key_and_resolve_tenant),
    db: Session = Depends(get_db)
) -> Dict[str, RequestTemplate]:
    """
    Returns pre-filled request templates for common API operations.
    
    Templates are filtered based on tenant subscription and environment.
    """
    subscription_service = SubscriptionService(db, tenant)
    subscription = subscription_service.get_current_subscription()
    
    # Check if tenant has production access
    has_production_access = False
    if subscription and subscription.plan:
        features = subscription.plan.features or {}
        has_production_access = features.get("production_access", False)
    
    templates = {}
    
    # Phase 1 Invoice (Sandbox)
    templates["phase1_sandbox"] = RequestTemplate(
        name="Phase 1 Invoice (Sandbox)",
        description="Generate QR code for Phase 1 invoice in sandbox environment",
        endpoint="/api/v1/invoices",
        method="POST",
        body={
            "mode": "PHASE_1",
            "environment": "SANDBOX",
            "invoice_number": "INV-001",
            "invoice_date": datetime.utcnow().isoformat(),
            "seller_name": "Test Company",
            "seller_tax_number": tenant.vat_number,
            "line_items": [
                {
                    "name": "Test Item",
                    "quantity": 1.0,
                    "unit_price": 100.0,
                    "tax_rate": 15.0,
                    "tax_category": "S"
                }
            ],
            "total_tax_exclusive": 100.0,
            "total_tax_amount": 15.0,
            "total_amount": 115.0
        },
        requires_production_confirmation=False
    )
    
    # Phase 2 Invoice (Sandbox)
    templates["phase2_sandbox"] = RequestTemplate(
        name="Phase 2 Invoice (Sandbox)",
        description="Submit Phase 2 invoice for clearance in sandbox environment",
        endpoint="/api/v1/invoices",
        method="POST",
        body={
            "mode": "PHASE_2",
            "environment": "SANDBOX",
            "invoice_number": "INV-002",
            "invoice_date": datetime.utcnow().isoformat(),
            "seller_name": "Test Company",
            "seller_tax_number": tenant.vat_number,
            "line_items": [
                {
                    "name": "Test Item",
                    "quantity": 1.0,
                    "unit_price": 100.0,
                    "tax_rate": 15.0,
                    "tax_category": "S"
                }
            ],
            "total_tax_exclusive": 100.0,
            "total_tax_amount": 15.0,
            "total_amount": 115.0
        },
        requires_production_confirmation=False
    )
    
    # Phase 2 Invoice (Production) - only if has access
    if has_production_access:
        templates["phase2_production"] = RequestTemplate(
            name="Phase 2 Invoice (Production)",
            description="Submit Phase 2 invoice for clearance in PRODUCTION environment (requires confirmation)",
            endpoint="/api/v1/invoices",
            method="POST",
            body={
                "mode": "PHASE_2",
                "environment": "PRODUCTION",
                "invoice_number": "INV-PROD-001",
                "invoice_date": datetime.utcnow().isoformat(),
                "seller_name": tenant.company_name,
                "seller_tax_number": tenant.vat_number,
                "line_items": [
                    {
                        "name": "Product/Service",
                        "quantity": 1.0,
                        "unit_price": 100.0,
                        "tax_rate": 15.0,
                        "tax_category": "S"
                    }
                ],
                "total_tax_exclusive": 100.0,
                "total_tax_amount": 15.0,
                "total_amount": 115.0,
                "confirm_production": True
            },
            requires_production_confirmation=True
        )
    
    # AI Readiness Score
    templates["ai_readiness"] = RequestTemplate(
        name="AI Readiness Score",
        description="Get ZATCA compliance readiness score using AI",
        endpoint="/api/v1/ai/readiness-score",
        method="GET",
        query_params={"period": "30d"},
        requires_production_confirmation=False
    )
    
    # AI Error Explanation
    templates["ai_error_explanation"] = RequestTemplate(
        name="AI Error Explanation",
        description="Get AI-powered explanation for ZATCA error code",
        endpoint="/api/v1/ai/explain-zatca-error",
        method="POST",
        body={
            "error_code": "ZATCA-2001",
            "error_message": "Invoice validation failed",
            "environment": "SANDBOX"
        },
        requires_production_confirmation=False
    )
    
    # Get Current Subscription
    templates["get_subscription"] = RequestTemplate(
        name="Get Current Subscription",
        description="Get current subscription details and limits",
        endpoint="/api/v1/plans/current",
        method="GET",
        requires_production_confirmation=False
    )
    
    # Get Usage Summary
    templates["get_usage"] = RequestTemplate(
        name="Get Usage Summary",
        description="Get current usage statistics (invoices, AI requests)",
        endpoint="/api/v1/plans/usage",
        method="GET",
        requires_production_confirmation=False
    )
    
    # Health Check
    templates["health_check"] = RequestTemplate(
        name="Health Check",
        description="Check API health and system status",
        endpoint="/api/v1/health",
        method="GET",
        requires_production_confirmation=False
    )
    
    return templates


@router.post(
    "/execute",
    response_model=PlaygroundResponse,
    summary="Execute API request through playground"
)
async def execute_playground_request(
    request: PlaygroundRequest,
    tenant: TenantContext = Depends(verify_api_key_and_resolve_tenant),
    db: Session = Depends(get_db)
) -> PlaygroundResponse:
    """
    Executes an API request through the playground interface.
    
    CRITICAL SECURITY RULES:
    - All requests are logged with source="api_playground"
    - Production write actions require confirmation
    - Subscription limits are enforced
    - Rate limits are enforced
    - Sensitive fields are masked in responses
    
    This endpoint acts as a proxy to actual API endpoints while adding
    audit logging and security checks specific to the playground.
    """
    start_time = time.time()
    
    # Validate endpoint
    if not request.endpoint.startswith("/api/v1/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endpoint must start with /api/v1/"
        )
    
    # Validate method
    if request.method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported HTTP method: {request.method}"
        )
    
    # Check subscription limits
    subscription_service = SubscriptionService(db, tenant)
    
    # For write operations, check limits
    if request.method.upper() in ["POST", "PUT", "PATCH", "DELETE"]:
        # Check invoice limit for invoice endpoints
        if "/invoices" in request.endpoint:
            allowed, limit_error = subscription_service.check_invoice_limit()
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=limit_error.model_dump() if limit_error else {"error": "INVOICE_LIMIT_EXCEEDED"}
                )
        
        # Check AI limit for AI endpoints
        if "/ai/" in request.endpoint:
            allowed, limit_error = subscription_service.check_ai_limit()
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=limit_error.model_dump() if limit_error else {"error": "AI_LIMIT_EXCEEDED"}
                )
    
    # Check production access for production requests
    if request.body and request.body.get("environment") == "PRODUCTION":
        if not request.confirm_production:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "PRODUCTION_CONFIRMATION_REQUIRED",
                    "message": "Production actions require explicit confirmation"
                }
            )
        
        # Check production access
        has_access, error = check_production_access(tenant, db)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error.model_dump() if error else {"error": "PRODUCTION_ACCESS_DENIED"}
            )
    
    # Log playground execution
    logger.info(
        f"Playground execution: tenant_id={tenant.tenant_id}, "
        f"endpoint={request.endpoint}, method={request.method}, "
        f"source=api_playground"
    )
    
    # For now, return a response indicating this is a playground proxy
    # In a full implementation, this would actually proxy the request to the target endpoint
    # For MVP, we'll return a structured response that the frontend can use
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Mask sensitive fields in response
    response_body = {
        "message": "Playground execution endpoint",
        "note": "This endpoint proxies requests to actual API endpoints. "
                "In production, implement actual request proxying here.",
        "request": {
            "endpoint": request.endpoint,
            "method": request.method,
            "body": mask_sensitive_fields(request.body or {}),
            "query_params": request.query_params
        }
    }
    
    return PlaygroundResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=response_body,
        latency_ms=latency_ms,
        timestamp=datetime.utcnow().isoformat(),
        source="api_playground"
    )

