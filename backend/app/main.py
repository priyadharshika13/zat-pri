"""
Application entry point for the ZATCA Compliance API.

Responsible for initializing the FastAPI application,
wiring core middleware, and registering versioned routes.

Notes:
- Business logic is delegated to service layers
- Configuration is loaded from environment-based settings
- Designed for production deployment
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import json

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.i18n import get_language_from_request, get_bilingual_error, Language
from app.api.v1.router import router as v1_router
from app.api.v1.routes.internal import router as internal_router


def create_application() -> FastAPI:
    """Creates and configures the FastAPI application."""
    settings = get_settings()

    # Swagger: when enable_docs is False, /docs and /openapi.json are not registered,
    # so GET /docs returns 404 with JSON {"detail": "Not Found"}.
    # Enable via ENABLE_DOCS=true or ENVIRONMENT_NAME=local|dev; disable in prod with ENVIRONMENT_NAME=production.
    application = FastAPI(
        title="ZATCA Compliance API",
        version="1.0.0",
        docs_url="/docs" ,
        redoc_url=None,
        openapi_url="/openapi.json",
    )

    # Root endpoint - provides basic API information
    @application.get("/", tags=["root"])
    async def root():
        """Root endpoint - provides basic API information."""
        return {
            "name": "ZATCA Compliance API",
            "version": "1.0.0",
            "status": "operational",
            "api_version": "v1",
            "api_base_url": "/api/v1",
            "health_check": "/api/v1/system/health",
            "docs": "/docs",
            "message": "Welcome to ZATCA Compliance API. Use /api/v1 endpoints to interact with the API."
        }

    application.include_router(v1_router, prefix="/api/v1")
    
    # Phase 9: Register internal router separately (protected with INTERNAL_SECRET_KEY)
    application.include_router(internal_router, prefix="/api/v1")

    register_lifecycle_events(application)
    register_exception_handlers(application)
    register_middleware(application)
    _register_openapi_security(application)

    return application


def _register_openapi_security(application: FastAPI) -> None:
    """
    Registers X-API-Key security scheme in OpenAPI so Swagger UI shows Authorize.
    Users enter the key once; it is sent with all requests. Backend enforcement
    remains via verify_api_key_and_resolve_tenant dependency on protected routes.
    """
    from fastapi.openapi.utils import get_openapi

    def custom_openapi():
        if application.openapi_schema is not None:
            return application.openapi_schema
        openapi_schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description or "",
            routes=application.routes,
        )
        openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
        openapi_schema["components"]["securitySchemes"]["ApiKeyAuth"] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for machine-to-machine authentication. Obtain from your tenant dashboard or support.",
        }
        # Apply to all API v1 paths so Swagger sends the key with every request
        openapi_schema["security"] = [{"ApiKeyAuth": []}]
        application.openapi_schema = openapi_schema
        return application.openapi_schema

    application.openapi = custom_openapi


def register_lifecycle_events(application: FastAPI) -> None:
    """Registers application lifecycle event handlers."""
    @application.on_event("startup")
    async def on_startup() -> None:
        setup_logging()
        
        # Initialize application start time for uptime tracking
        from app.api.v1.routes.system import set_application_start_time
        set_application_start_time()
        
        # Seed default tenant and plans in local/dev environments
        try:
            from app.db.session import SessionLocal
            from app.services.tenant_seed_service import seed_tenants_if_needed
            from app.services.plan_seed_service import seed_plans_if_needed
            from app.core.config import get_settings
            
            settings = get_settings()
            db = SessionLocal()
            try:
                seed_tenants_if_needed(db, settings.environment_name)
                seed_plans_if_needed(db, settings.environment_name)
            finally:
                db.close()
        except Exception as e:
            # Log but don't fail startup if seeding fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Seeding failed (non-critical): {e}")

    @application.on_event("shutdown")
    async def on_shutdown() -> None:
        pass


def register_exception_handlers(application: FastAPI) -> None:
    """Registers global exception handlers."""
    
    @application.exception_handler(json.JSONDecodeError)
    async def json_decode_exception_handler(
        request: Request, exc: json.JSONDecodeError
    ) -> JSONResponse:
        """
        Handles JSON parsing errors with clear, actionable error messages.
        
        CRITICAL: This prevents PowerShell curl.exe -d "{...}" malformed JSON errors
        from crashing the application. Provides clear guidance on correct usage.
        """
        language = get_language_from_request(request)
        
        error_msg_en = (
            f"Invalid JSON format: {str(exc)}. "
            f"Please ensure your request body is valid JSON. "
            f"Use file-based requests (--data-binary @file.json) or properly escaped JSON strings."
        )
        error_msg_ar = (
            f"تنسيق JSON غير صالح: {str(exc)}. "
            f"يرجى التأكد من أن نص الطلب بتنسيق JSON صحيح. "
            f"استخدم الطلبات المستندة إلى الملفات (--data-binary @file.json) أو سلاسل JSON محمية بشكل صحيح."
        )
        
        error_detail = {
            "error": "INVALID_JSON",
            "message": error_msg_en,
            "message_ar": error_msg_ar,
            "hint": (
                "For PowerShell: Use Invoke-RestMethod with -Body (Get-Content -Raw file.json). "
                "For curl: Use --data-binary @file.json instead of inline -d strings."
            ),
            "hint_ar": (
                "لـ PowerShell: استخدم Invoke-RestMethod مع -Body (Get-Content -Raw file.json). "
                "لـ curl: استخدم --data-binary @file.json بدلاً من سلاسل -d المضمنة."
            )
        }
        
        return JSONResponse(
            status_code=400,
            content=error_detail
        )
    
    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handles Pydantic validation errors with bilingual messages."""
        language = get_language_from_request(request)
        
        # Check if this is a Phase-2 validation error (from model_post_init)
        is_phase2_error = False
        phase2_hint = None
        for error in exc.errors():
            error_msg = error.get("msg", "")
            if "Phase-2" in error_msg or "phase-2" in error_msg.lower():
                is_phase2_error = True
                phase2_hint = (
                    "Phase-2 invoices require: seller_tax_number, invoice_type, uuid. (previous_invoice_hash optional for first invoice.) "
                    "See sample_phase2_payload.json for correct format."
                )
                break
        
        # Format validation errors
        errors = []
        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error.get("loc", []))
            error_msg = error.get("msg", "Validation error")
            error_type = error.get("type", "value_error")
            
            # Get bilingual error message
            if language == Language.AR:
                # Arabic validation messages
                if error_type == "missing":
                    msg_ar = f"الحقل '{field_path}' مطلوب"
                    msg_en = f"Field '{field_path}' is required"
                elif error_type == "value_error":
                    msg_ar = f"قيمة غير صالحة للحقل '{field_path}': {error_msg}"
                    msg_en = f"Invalid value for field '{field_path}': {error_msg}"
                elif error_type == "type_error":
                    msg_ar = f"نوع غير صحيح للحقل '{field_path}'"
                    msg_en = f"Wrong type for field '{field_path}'"
                else:
                    msg_ar = f"خطأ في التحقق من '{field_path}': {error_msg}"
                    msg_en = f"Validation error for '{field_path}': {error_msg}"
            else:
                msg_en = f"Field '{field_path}': {error_msg}"
                msg_ar = f"الحقل '{field_path}': {error_msg}"
            
            errors.append({
                "field": field_path,
                "message": msg_en,
                "message_ar": msg_ar,
                "type": error_type
            })
        
        error_detail = get_bilingual_error("VALIDATION_ERROR")
        error_detail["errors"] = errors
        
        # Add Phase-2 specific hint if applicable
        if is_phase2_error:
            error_detail["error"] = "PHASE2_VALIDATION_ERROR"
            error_detail["hint"] = phase2_hint
            error_detail["hint_ar"] = (
                "تتطلب فواتير المرحلة الثانية: seller_tax_number, invoice_type, uuid. (previous_invoice_hash اختياري للفاتورة الأولى.) "
                "راجع sample_phase2_payload.json للحصول على التنسيق الصحيح."
            )
        
        return JSONResponse(
            status_code=422,
            content=error_detail
        )
    
    @application.exception_handler(ValueError)
    async def value_error_exception_handler(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        """
        Handles ValueError exceptions (e.g., Phase-2 mandatory field validation).
        
        CRITICAL: This catches validation errors from model_post_init and other
        business logic validations, providing clear error messages.
        """
        language = get_language_from_request(request)
        error_msg = str(exc)
        
        # Check if this is a Phase-2 validation error
        if "Phase-2" in error_msg or "phase-2" in error_msg.lower():
            error_detail = {
                "error": "PHASE2_VALIDATION_ERROR",
                "message": error_msg,
                "message_ar": (
                    f"خطأ في التحقق من صحة فاتورة المرحلة الثانية: {error_msg}"
                ),
                "hint": (
                    "Phase-2 invoices require: seller_tax_number, invoice_type, uuid. (previous_invoice_hash optional for first invoice.) "
                    "See sample_phase2_payload.json for correct format."
                ),
                "hint_ar": (
                    "تتطلب فواتير المرحلة الثانية: seller_tax_number, invoice_type, uuid. (previous_invoice_hash اختياري للفاتورة الأولى.) "
                    "راجع sample_phase2_payload.json للحصول على التنسيق الصحيح."
                )
            }
            status_code = 422
        else:
            error_detail = {
                "error": "VALIDATION_ERROR",
                "message": error_msg,
                "message_ar": f"خطأ في التحقق: {error_msg}"
            }
            status_code = 400
        
        return JSONResponse(
            status_code=status_code,
            content=error_detail
        )
    
    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handles unhandled exceptions with bilingual messages."""
        language = get_language_from_request(request)
        error_detail = get_bilingual_error("SERVER_ERROR")
        
        return JSONResponse(
            status_code=500,
            content=error_detail
        )


def register_middleware(application: FastAPI) -> None:
    """Registers application middleware."""
    from fastapi.middleware.cors import CORSMiddleware
    from app.middleware.security_headers import SecurityHeadersMiddleware
    from app.middleware.audit import AuditMiddleware
    from app.middleware.rate_limit import RateLimitMiddleware
    from app.middleware.docs_localhost import DocsLocalhostMiddleware
    from app.services.subscription_service import SubscriptionService

    # Docs localhost restriction: first added = runs last (closest to request).
    # When DOCS_LOCALHOST_ONLY=true, /docs and /openapi.json only from 127.0.0.1 / ::1
    application.add_middleware(DocsLocalhostMiddleware)
    
    # Security headers should be added next (outermost middleware)
    # This ensures all responses get security headers
    application.add_middleware(SecurityHeadersMiddleware)
    
    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Rate limiting must come after tenant resolution (in security dependency)
    # So it's added after CORS but before audit
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(AuditMiddleware)


app = create_application()

