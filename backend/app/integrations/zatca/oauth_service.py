"""
ZATCA OAuth client-credentials flow service.

Handles OAuth token generation, caching, and refresh for ZATCA sandbox and production APIs.
Implements client-credentials grant type with automatic token refresh on expiry or 401 errors.
"""

import logging
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict
import asyncio
from threading import Lock

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ZatcaAccessToken:
    """
    OAuth access token with expiry tracking.
    
    Attributes:
        access_token: The OAuth access token string
        token_type: Token type (typically "Bearer")
        expires_at: Datetime when token expires (with 60s buffer)
        expires_in: Original expiry time in seconds
    """
    
    def __init__(self, access_token: str, token_type: str, expires_in: int):
        """
        Initializes access token with expiry tracking.
        
        Args:
            access_token: OAuth access token
            token_type: Token type (e.g., "Bearer")
            expires_in: Expiry time in seconds
        """
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in
        
        # Set expiry with 60 second buffer to avoid edge cases
        self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
    
    def is_valid(self) -> bool:
        """
        Checks if token is still valid.
        
        Returns:
            True if token is valid, False if expired
        """
        return datetime.utcnow() < self.expires_at
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ZatcaAccessToken(expires_at={self.expires_at}, is_valid={self.is_valid()})"


class ZatcaOAuthService:
    """
    OAuth client-credentials service for ZATCA API authentication.
    
    Handles token generation, caching, and automatic refresh.
    Thread-safe token caching with automatic expiry management.
    """
    
    def __init__(self, environment: str = "SANDBOX"):
        """
        Initializes OAuth service for specified environment.
        
        Args:
            environment: ZATCA environment ("SANDBOX" or "PRODUCTION")
        """
        self.environment = environment.upper()
        settings = get_settings()
        
        # Get environment-specific configuration
        if self.environment == "SANDBOX":
            self.base_url = settings.zatca_sandbox_base_url
            self.client_id = getattr(settings, "zatca_sandbox_client_id", None)
            self.client_secret = getattr(settings, "zatca_sandbox_client_secret", None)
        elif self.environment == "PRODUCTION":
            self.base_url = settings.zatca_production_base_url
            self.client_id = getattr(settings, "zatca_production_client_id", None)
            self.client_secret = getattr(settings, "zatca_production_client_secret", None)
        else:
            raise ValueError(f"Invalid environment: {environment}. Must be SANDBOX or PRODUCTION")
        
        # OAuth timeout (default 10 seconds)
        self.oauth_timeout = float(getattr(settings, "zatca_oauth_timeout", 10.0))
        
        # Token cache (in-memory, thread-safe)
        self._token_cache: Optional[ZatcaAccessToken] = None
        self._token_lock = Lock()
        self._refresh_lock = asyncio.Lock()
        
        # Validate credentials are configured
        if not self.client_id or not self.client_secret:
            logger.warning(
                f"ZATCA OAuth credentials not configured for {self.environment}. "
                f"Set ZATCA_{self.environment}_CLIENT_ID and ZATCA_{self.environment}_CLIENT_SECRET"
            )
    
    def _get_basic_auth_header(self) -> str:
        """
        Generates Basic Authentication header for OAuth token request.
        
        Format: base64(client_id:client_secret)
        
        Returns:
            Basic auth header value
        """
        if not self.client_id or not self.client_secret:
            raise ValueError(
                f"ZATCA OAuth credentials not configured for {self.environment}. "
                f"Set ZATCA_{self.environment}_CLIENT_ID and ZATCA_{self.environment}_CLIENT_SECRET"
            )
        
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return f"Basic {encoded}"
    
    async def _fetch_token(self) -> ZatcaAccessToken:
        """
        Fetches new OAuth token from ZATCA.
        
        Returns:
            ZatcaAccessToken instance
            
        Raises:
            httpx.HTTPStatusError: If OAuth request fails
            ValueError: If credentials are invalid or response is malformed
        """
        if not self.client_id or not self.client_secret:
            raise ValueError(
                f"ZATCA OAuth credentials not configured for {self.environment}. "
                f"Set ZATCA_{self.environment}_CLIENT_ID and ZATCA_{self.environment}_CLIENT_SECRET"
            )
        
        oauth_url = f"{self.base_url}/oauth/token"
        timeout = httpx.Timeout(self.oauth_timeout, connect=5.0)
        
        logger.info(
            f"Fetching OAuth token from ZATCA {self.environment}",
            extra={
                "environment": self.environment,
                "oauth_url": oauth_url
            }
        )
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    oauth_url,
                    headers={
                        "Authorization": self._get_basic_auth_header(),
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    data={
                        "grant_type": "client_credentials"
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Validate response structure
                if "access_token" not in data:
                    raise ValueError(f"Invalid OAuth response: missing access_token. Response: {data}")
                
                access_token = data.get("access_token")
                token_type = data.get("token_type", "Bearer")
                expires_in = int(data.get("expires_in", 3600))
                
                token = ZatcaAccessToken(
                    access_token=access_token,
                    token_type=token_type,
                    expires_in=expires_in
                )
                
                logger.info(
                    f"Successfully fetched OAuth token for {self.environment}",
                    extra={
                        "environment": self.environment,
                        "expires_at": token.expires_at.isoformat(),
                        "expires_in": expires_in
                    }
                )
                
                return token
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error(
                    f"OAuth authentication failed for {self.environment}: Invalid client credentials",
                    extra={
                        "environment": self.environment,
                        "status_code": e.response.status_code,
                        "error": e.response.text[:200]
                    }
                )
                raise ValueError(
                    f"Invalid ZATCA OAuth credentials for {self.environment}. "
                    f"Please verify ZATCA_{self.environment}_CLIENT_ID and ZATCA_{self.environment}_CLIENT_SECRET"
                ) from e
            else:
                logger.error(
                    f"OAuth token request failed for {self.environment}: HTTP {e.response.status_code}",
                    extra={
                        "environment": self.environment,
                        "status_code": e.response.status_code,
                        "error": e.response.text[:200]
                    }
                )
                raise
        except httpx.TimeoutException as e:
            logger.error(
                f"OAuth token request timeout for {self.environment}",
                extra={
                    "environment": self.environment,
                    "timeout": self.oauth_timeout
                }
            )
            raise ValueError(
                f"OAuth token request timed out for {self.environment}. "
                f"Please check network connectivity and ZATCA service availability"
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected error fetching OAuth token for {self.environment}: {e}",
                extra={
                    "environment": self.environment,
                    "error": str(e)
                },
                exc_info=True
            )
            raise ValueError(f"Failed to fetch OAuth token: {str(e)}") from e
    
    async def get_access_token(self, force_refresh: bool = False) -> ZatcaAccessToken:
        """
        Gets valid OAuth access token, using cache if available and valid.
        
        Args:
            force_refresh: If True, force token refresh even if cached token is valid
            
        Returns:
            ZatcaAccessToken instance
            
        Raises:
            ValueError: If credentials are invalid or OAuth request fails
        """
        # Check cache first (thread-safe read)
        with self._token_lock:
            cached_token = self._token_cache
        
        # Return cached token if valid and not forcing refresh
        if not force_refresh and cached_token and cached_token.is_valid():
            logger.debug(
                f"Using cached OAuth token for {self.environment}",
                extra={
                    "environment": self.environment,
                    "expires_at": cached_token.expires_at.isoformat()
                }
            )
            return cached_token
        
        # Acquire async lock for token refresh (prevent concurrent refreshes)
        async with self._refresh_lock:
            # Double-check cache after acquiring lock (another thread may have refreshed)
            with self._token_lock:
                cached_token = self._token_cache
            
            if not force_refresh and cached_token and cached_token.is_valid():
                logger.debug(
                    f"Using cached OAuth token for {self.environment} (after lock)",
                    extra={
                        "environment": self.environment,
                        "expires_at": cached_token.expires_at.isoformat()
                    }
                )
                return cached_token
            
            # Fetch new token
            logger.info(
                f"Refreshing OAuth token for {self.environment}",
                extra={"environment": self.environment}
            )
            
            new_token = await self._fetch_token()
            
            # Update cache (thread-safe write)
            with self._token_lock:
                self._token_cache = new_token
            
            return new_token
    
    async def refresh_token(self) -> ZatcaAccessToken:
        """
        Forces token refresh.
        
        Returns:
            New ZatcaAccessToken instance
        """
        return await self.get_access_token(force_refresh=True)
    
    def clear_cache(self) -> None:
        """
        Clears cached token (for testing or manual refresh).
        """
        with self._token_lock:
            self._token_cache = None
        logger.debug(f"Cleared OAuth token cache for {self.environment}")


# Global OAuth service instances (singleton per environment)
_sandbox_oauth_service: Optional[ZatcaOAuthService] = None
_production_oauth_service: Optional[ZatcaOAuthService] = None


def get_oauth_service(environment: str = "SANDBOX") -> ZatcaOAuthService:
    """
    Gets OAuth service instance for specified environment (singleton pattern).
    
    Args:
        environment: ZATCA environment ("SANDBOX" or "PRODUCTION")
        
    Returns:
        ZatcaOAuthService instance
    """
    global _sandbox_oauth_service, _production_oauth_service
    
    env_upper = environment.upper()
    
    if env_upper == "SANDBOX":
        if _sandbox_oauth_service is None:
            _sandbox_oauth_service = ZatcaOAuthService(environment="SANDBOX")
        return _sandbox_oauth_service
    elif env_upper == "PRODUCTION":
        if _production_oauth_service is None:
            _production_oauth_service = ZatcaOAuthService(environment="PRODUCTION")
        return _production_oauth_service
    else:
        raise ValueError(f"Invalid environment: {environment}. Must be SANDBOX or PRODUCTION")

