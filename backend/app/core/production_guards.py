"""
Production safety guards and environment hardening.

Enforces production access restrictions and confirmation requirements.
Prevents accidental legal submissions and unauthorized production access.
"""

import logging
from typing import Optional
from fastapi import HTTPException, status

from app.schemas.invoice import InvoiceRequest
from app.schemas.auth import TenantContext
from app.services.subscription_service import SubscriptionService
from app.models.subscription import SubscriptionStatus
from app.core.constants import Environment
from app.db.session import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# Plans that allow production access (paid plans only)
PRODUCTION_ALLOWED_PLANS = {"Starter", "Pro", "Enterprise"}

# Plans that are restricted from production (free/trial plans)
PRODUCTION_RESTRICTED_PLANS = {"Free Sandbox", "Trial"}


def check_production_access(
    tenant_context: TenantContext,
    db: Session,
    environment: Environment
) -> None:
    """
    Checks if tenant has access to production environment.
    
    CRITICAL: Only paid plans (Starter, Pro, Enterprise) can submit to Production.
    Trial and Free Sandbox plans are restricted to Sandbox only.
    
    Args:
        tenant_context: Tenant context from request
        db: Database session
        environment: Target environment (SANDBOX or PRODUCTION)
        
    Raises:
        HTTPException: If production access is denied
    """
    # Sandbox is always allowed
    if environment == Environment.SANDBOX:
        return
    
    # Production requires paid plan
    if environment == Environment.PRODUCTION:
        subscription_service = SubscriptionService(db, tenant_context)
        subscription = subscription_service.get_current_subscription()
        
        if not subscription:
            logger.warning(
                f"Production access denied: tenant_id={tenant_context.tenant_id}, "
                f"reason=no_subscription"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "PRODUCTION_ACCESS_DENIED",
                    "message": "Production access requires an active paid plan",
                    "message_ar": "يتطلب الوصول إلى الإنتاج خطة مدفوعة نشطة",
                    "reason": "no_subscription"
                }
            )
        
        plan_name = subscription.plan.name if subscription.plan else None
        
        if plan_name in PRODUCTION_RESTRICTED_PLANS:
            logger.warning(
                f"Production access denied: tenant_id={tenant_context.tenant_id}, "
                f"plan={plan_name}, reason=restricted_plan"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "PRODUCTION_ACCESS_DENIED",
                    "message": "Production access requires an active paid plan",
                    "message_ar": "يتطلب الوصول إلى الإنتاج خطة مدفوعة نشطة",
                    "reason": "restricted_plan",
                    "current_plan": plan_name
                }
            )
        
        if plan_name not in PRODUCTION_ALLOWED_PLANS:
            # Check if plan has production_access feature flag (features may be None)
            plan_features = (getattr(subscription.plan, "features", None) or {}) if subscription.plan else {}
            if not plan_features.get("production_access", False):
                logger.warning(
                    f"Production access denied: tenant_id={tenant_context.tenant_id}, "
                    f"plan={plan_name}, reason=no_production_feature"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "PRODUCTION_ACCESS_DENIED",
                        "message": "Production access requires an active paid plan",
                        "message_ar": "يتطلب الوصول إلى الإنتاج خطة مدفوعة نشطة",
                        "reason": "no_production_feature",
                        "current_plan": plan_name
                    }
                )


def require_production_confirmation(
    request: InvoiceRequest,
    confirm_production: Optional[bool] = None
) -> None:
    """
    Requires explicit confirmation for production invoice submissions.
    
    CRITICAL: This prevents accidental legal submissions to Production ZATCA.
    All production submissions MUST include confirm_production=true.
    
    Args:
        request: Invoice request
        confirm_production: Explicit confirmation flag from request
        
    Raises:
        HTTPException: If confirmation is missing for production submissions
    """
    if request.environment == Environment.PRODUCTION:
        if confirm_production is not True:
            logger.warning(
                f"Production submission rejected: invoice_number={request.invoice_number}, "
                f"reason=missing_confirmation"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "PRODUCTION_CONFIRMATION_REQUIRED",
                    "message": "Production submissions require explicit confirmation. Include 'confirm_production=true' in your request.",
                    "message_ar": "تتطلب عمليات الإرسال إلى الإنتاج تأكيدًا صريحًا. قم بتضمين 'confirm_production=true' في طلبك.",
                    "reason": "missing_confirmation"
                }
            )


def validate_write_action(
    tenant_context: TenantContext,
    db: Session,
    action_name: str
) -> None:
    """
    Validates that tenant can perform write actions.
    
    Write actions are blocked for:
    - EXPIRED subscriptions
    - SUSPENDED subscriptions
    
    Args:
        tenant_context: Tenant context from request
        db: Database session
        action_name: Name of the action being performed (for logging)
        
    Raises:
        HTTPException: If write action is not allowed
    """
    subscription_service = SubscriptionService(db, tenant_context)
    subscription = subscription_service.get_current_subscription()
    
    if not subscription:
        logger.warning(
            f"Write action denied: tenant_id={tenant_context.tenant_id}, "
            f"action={action_name}, reason=no_subscription"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "WRITE_ACTION_DENIED",
                "message": "Write actions require an active subscription",
                "message_ar": "تتطلب الإجراءات الكتابية اشتراكًا نشطًا",
                "reason": "no_subscription"
            }
        )
    
    if subscription.status == SubscriptionStatus.EXPIRED:
        logger.warning(
            f"Write action denied: tenant_id={tenant_context.tenant_id}, "
            f"action={action_name}, reason=expired_subscription"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "WRITE_ACTION_DENIED",
                "message": "Write actions are not allowed for expired subscriptions. Please renew your subscription.",
                "message_ar": "لا يُسمح بالإجراءات الكتابية للاشتراكات المنتهية. يرجى تجديد اشتراكك.",
                "reason": "expired_subscription"
            }
        )
    
    if subscription.status == SubscriptionStatus.SUSPENDED:
        logger.warning(
            f"Write action denied: tenant_id={tenant_context.tenant_id}, "
            f"action={action_name}, reason=suspended_subscription"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "WRITE_ACTION_DENIED",
                "message": "Write actions are not allowed for suspended subscriptions. Please contact support.",
                "message_ar": "لا يُسمح بالإجراءات الكتابية للاشتراكات المعلقة. يرجى الاتصال بالدعم.",
                "reason": "suspended_subscription"
            }
        )

