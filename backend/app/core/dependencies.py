"""
FastAPI dependencies for language detection and i18n support.

Provides dependency injection for language detection from request headers/query params.
"""

from fastapi import Request, Depends
from typing import Annotated
from app.core.i18n import get_language_from_request, Language


def get_language(request: Request) -> Language:
    """
    FastAPI dependency to extract language from request.
    
    Priority:
    1. lang query parameter
    2. Accept-Language header
    3. Default to English
    
    Usage:
        @router.get("/endpoint")
        async def my_endpoint(lang: Annotated[Language, Depends(get_language)]):
            # Use lang to determine response language
            pass
    """
    return get_language_from_request(request)


# Type alias for dependency injection
LanguageDep = Annotated[Language, Depends(get_language)]

