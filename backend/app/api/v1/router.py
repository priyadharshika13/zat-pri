"""
API version 1 router aggregation.

Combines all v1 route modules into a single router for registration.
Does not contain route implementations - delegates to route modules.
"""

from fastapi import APIRouter

from app.api.v1.routes.invoices import router as invoices_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.plans import router as plans_router
from app.api.v1.routes.errors import router as errors_router
from app.api.v1.routes.ai import router as ai_router
from app.api.v1.routes.tenants import router as tenants_router
from app.api.v1.routes.api_keys import router as api_keys_router
from app.api.v1.routes.certificates import router as certificates_router
from app.api.v1.routes.system import router as system_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.playground import router as playground_router
from app.api.v1.routes.reports import router as reports_router
from app.api.v1.routes.exports import router as exports_router
from app.api.v1.routes.webhooks import router as webhooks_router
from app.api.v1.routes.zatca import router as zatca_router
# Phase 9: Internal routes (NOT included in public router - registered separately in main.py)

router = APIRouter()

router.include_router(auth_router)
router.include_router(invoices_router)
router.include_router(health_router)
router.include_router(plans_router)
router.include_router(errors_router)
router.include_router(ai_router)
router.include_router(tenants_router)
router.include_router(api_keys_router)
router.include_router(certificates_router)
router.include_router(system_router)
router.include_router(playground_router)
router.include_router(reports_router)
router.include_router(exports_router)
router.include_router(webhooks_router)
router.include_router(zatca_router)
# NOTE: Internal router is registered separately in main.py to keep it isolated
