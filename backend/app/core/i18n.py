"""
Internationalization (i18n) utilities for bilingual support.

Provides language detection from Accept-Language header or query parameters,
and centralized error catalog with bilingual messages.
"""

from typing import Optional
from fastapi import Request
from enum import Enum


class Language(str, Enum):
    """Supported languages."""
    EN = "en"
    AR = "ar"


# Centralized error catalog with bilingual messages
ERROR_CATALOG: dict[str, dict[str, str]] = {
    # Generic errors
    "GENERIC_ERROR": {
        "message_en": "An error occurred",
        "message_ar": "حدث خطأ"
    },
    "VALIDATION_ERROR": {
        "message_en": "Validation error",
        "message_ar": "خطأ في التحقق"
    },
    "UNAUTHORIZED": {
        "message_en": "Unauthorized. Please check your API key.",
        "message_ar": "غير مصرح. يرجى التحقق من مفتاح API الخاص بك."
    },
    "FORBIDDEN": {
        "message_en": "Access forbidden",
        "message_ar": "الوصول محظور"
    },
    "NOT_FOUND": {
        "message_en": "Resource not found",
        "message_ar": "المورد غير موجود"
    },
    "SERVER_ERROR": {
        "message_en": "Server error. Please try again later.",
        "message_ar": "خطأ في الخادم. يرجى المحاولة مرة أخرى لاحقًا."
    },
    "TIMEOUT": {
        "message_en": "Request timeout. Please try again.",
        "message_ar": "انتهت مهلة الطلب. يرجى المحاولة مرة أخرى."
    },
    
    # ZATCA errors
    "ZATCA_TIMEOUT": {
        "message_en": "ZATCA API request timed out. Please try again later.",
        "message_ar": "انتهت مهلة طلب ZATCA. يرجى المحاولة مرة أخرى لاحقًا."
    },
    "ZATCA_SERVER_ERROR": {
        "message_en": "ZATCA API is currently unavailable. Please try again later.",
        "message_ar": "واجهة ZATCA غير متاحة حاليًا. يرجى المحاولة مرة أخرى لاحقًا."
    },
    "ZATCA_CLIENT_ERROR": {
        "message_en": "ZATCA API returned an error. Please check your request.",
        "message_ar": "أعادت واجهة ZATCA خطأ. يرجى التحقق من طلبك."
    },
    "ZATCA_ERROR": {
        "message_en": "ZATCA API request failed. Please try again later.",
        "message_ar": "فشل طلب واجهة ZATCA. يرجى المحاولة مرة أخرى لاحقًا."
    },
    
    # AI errors
    "AI_PROVIDER_TIMEOUT": {
        "message_en": "AI service request timed out. Please try again later.",
        "message_ar": "انتهت مهلة طلب خدمة AI. يرجى المحاولة مرة أخرى لاحقًا."
    },
    "AI_PROVIDER_ERROR": {
        "message_en": "AI service is currently unavailable. Please try again later.",
        "message_ar": "خدمة AI غير متاحة حاليًا. يرجى المحاولة مرة أخرى لاحقًا."
    },
    "AI_RATE_LIMIT": {
        "message_en": "AI service rate limit exceeded. Please try again later.",
        "message_ar": "تم تجاوز حد معدل خدمة AI. يرجى المحاولة مرة أخرى لاحقًا."
    },
    
    # Subscription errors
    "RATE_LIMIT_EXCEEDED": {
        "message_en": "Rate limit exceeded. Please slow down your requests.",
        "message_ar": "تم تجاوز حد المعدل. يرجى إبطاء طلباتك."
    },
    "SUBSCRIPTION_LIMIT_EXCEEDED": {
        "message_en": "Subscription limit exceeded. Please upgrade your plan.",
        "message_ar": "تم تجاوز حد الاشتراك. يرجى ترقية خطتك."
    },
    
    # Invoice errors
    "INVOICE_NOT_FOUND": {
        "message_en": "Invoice not found",
        "message_ar": "الفاتورة غير موجودة"
    },
    "INVOICE_CREATION_FAILED": {
        "message_en": "Failed to create invoice. Please try again.",
        "message_ar": "فشل إنشاء الفاتورة. يرجى المحاولة مرة أخرى."
    },
    "INVOICE_VALIDATION_FAILED": {
        "message_en": "Invoice validation failed. Please check your invoice data.",
        "message_ar": "فشل التحقق من الفاتورة. يرجى التحقق من بيانات الفاتورة."
    },
    
    # Webhook errors
    "WEBHOOK_NOT_FOUND": {
        "message_en": "Webhook not found",
        "message_ar": "الويب هوك غير موجود"
    },
    "WEBHOOK_DELIVERY_FAILED": {
        "message_en": "Webhook delivery failed. Please check your webhook URL.",
        "message_ar": "فشل تسليم الويب هوك. يرجى التحقق من رابط الويب هوك الخاص بك."
    },
}

# Invoice status translations
INVOICE_STATUS_LABELS: dict[str, dict[str, str]] = {
    "CREATED": {
        "label_en": "Created",
        "label_ar": "تم الإنشاء"
    },
    "PROCESSING": {
        "label_en": "Processing",
        "label_ar": "قيد المعالجة"
    },
    "CLEARED": {
        "label_en": "Cleared",
        "label_ar": "تم الاعتماد"
    },
    "REJECTED": {
        "label_en": "Rejected",
        "label_ar": "مرفوض"
    },
    "FAILED": {
        "label_en": "Failed",
        "label_ar": "فشل"
    },
}

# Webhook event translations
WEBHOOK_EVENT_LABELS: dict[str, dict[str, str]] = {
    "invoice.cleared": {
        "event_name_en": "Invoice Cleared",
        "event_name_ar": "تم اعتماد الفاتورة",
        "description_en": "Invoice successfully cleared by ZATCA",
        "description_ar": "تم اعتماد الفاتورة بنجاح من قبل ZATCA"
    },
    "invoice.rejected": {
        "event_name_en": "Invoice Rejected",
        "event_name_ar": "تم رفض الفاتورة",
        "description_en": "Invoice rejected by ZATCA or validation",
        "description_ar": "تم رفض الفاتورة من قبل ZATCA أو التحقق"
    },
    "invoice.failed": {
        "event_name_en": "Invoice Failed",
        "event_name_ar": "فشلت الفاتورة",
        "description_en": "Invoice processing failed due to system error",
        "description_ar": "فشل معالجة الفاتورة بسبب خطأ في النظام"
    },
    "invoice.retry_started": {
        "event_name_en": "Invoice Retry Started",
        "event_name_ar": "بدء إعادة محاولة الفاتورة",
        "description_en": "Invoice retry processing started",
        "description_ar": "تم بدء إعادة معالجة الفاتورة"
    },
    "invoice.retry_completed": {
        "event_name_en": "Invoice Retry Completed",
        "event_name_ar": "اكتملت إعادة محاولة الفاتورة",
        "description_en": "Invoice retry processing completed",
        "description_ar": "اكتملت إعادة معالجة الفاتورة"
    },
}


def get_invoice_status_label(status: str, language: Language = Language.EN) -> str:
    """
    Get invoice status label in the specified language.
    
    Args:
        status: Invoice status (CREATED, PROCESSING, CLEARED, REJECTED, FAILED)
        language: Target language
        
    Returns:
        Status label in the specified language
    """
    status_upper = status.upper()
    status_info = INVOICE_STATUS_LABELS.get(status_upper, {})
    
    if language == Language.AR:
        return status_info.get("label_ar", status_info.get("label_en", status))
    else:
        return status_info.get("label_en", status)


def get_bilingual_invoice_status(status: str) -> dict[str, str]:
    """
    Get bilingual invoice status labels.
    
    Args:
        status: Invoice status
        
    Returns:
        Dictionary with label_en and label_ar
    """
    status_upper = status.upper()
    status_info = INVOICE_STATUS_LABELS.get(status_upper, {})
    
    return {
        "status": status_upper,
        "label_en": status_info.get("label_en", status_upper),
        "label_ar": status_info.get("label_ar", status_upper)
    }


def get_webhook_event_labels(event_type: str) -> dict[str, str]:
    """
    Get bilingual webhook event labels.
    
    Args:
        event_type: Webhook event type (e.g., "invoice.cleared")
        
    Returns:
        Dictionary with event_name_en, event_name_ar, description_en, description_ar
    """
    event_info = WEBHOOK_EVENT_LABELS.get(event_type, {})
    
    return {
        "event": event_type,
        "event_name_en": event_info.get("event_name_en", event_type),
        "event_name_ar": event_info.get("event_name_ar", event_type),
        "description_en": event_info.get("description_en", ""),
        "description_ar": event_info.get("description_ar", "")
    }


def get_language_from_request(request: Request) -> Language:
    """
    Extract language from request.
    
    Priority:
    1. lang query parameter
    2. Accept-Language header
    3. Default to English
    
    Args:
        request: FastAPI request object
        
    Returns:
        Language enum value
    """
    # Check query parameter first
    lang_param = request.query_params.get("lang", "").lower()
    if lang_param in ["ar", "arabic"]:
        return Language.AR
    if lang_param in ["en", "english"]:
        return Language.EN
    
    # Check Accept-Language header
    accept_language = request.headers.get("Accept-Language", "")
    if accept_language:
        # Parse Accept-Language header (e.g., "ar-SA,ar;q=0.9,en;q=0.8")
        languages = accept_language.split(",")
        for lang in languages:
            lang_code = lang.split(";")[0].strip().lower()
            if lang_code.startswith("ar"):
                return Language.AR
            if lang_code.startswith("en"):
                return Language.EN
    
    # Default to English
    return Language.EN


def get_error_message(error_code: str, language: Language = Language.EN) -> str:
    """
    Get error message for a given error code in the specified language.
    
    Args:
        error_code: Error code key
        language: Target language
        
    Returns:
        Error message in the specified language, or English fallback
    """
    error_info = ERROR_CATALOG.get(error_code)
    if not error_info:
        # Fallback to generic error
        error_info = ERROR_CATALOG.get("GENERIC_ERROR", {})
    
    if language == Language.AR:
        return error_info.get("message_ar", error_info.get("message_en", "حدث خطأ"))
    else:
        return error_info.get("message_en", "An error occurred")


def get_bilingual_error(error_code: str) -> dict[str, str]:
    """
    Get bilingual error message for a given error code.
    
    Args:
        error_code: Error code key
        
    Returns:
        Dictionary with message_en and message_ar
    """
    error_info = ERROR_CATALOG.get(error_code)
    if not error_info:
        error_info = ERROR_CATALOG.get("GENERIC_ERROR", {})
    
    return {
        "error_code": error_code,
        "message_en": error_info.get("message_en", "An error occurred"),
        "message_ar": error_info.get("message_ar", "حدث خطأ")
    }

