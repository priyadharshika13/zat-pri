"""
Application configuration management.

Centralizes environment variables, settings, and configuration constants.
Handles validation of required settings and provides type-safe access to configuration.
Does not handle runtime configuration changes or dynamic reloading.
"""

from enum import Enum
from typing import Optional
from pathlib import Path
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Supported deployment environments."""
    SANDBOX = "sandbox"
    PRODUCTION = "production"


# Determine .env file location at module load time
# Use absolute paths to ensure it works regardless of current working directory
# Path: backend/app/core/config.py -> backend/app/core -> backend/app -> backend -> project_root
_CONFIG_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _CONFIG_DIR.parent.parent.parent
_ENV_FILE_ROOT = _PROJECT_ROOT / ".env"
_ENV_FILE_LOCAL = Path(".env").resolve() if Path(".env").exists() else None

# Use project root .env if it exists, otherwise current directory .env (if exists)
_ENV_FILE = str(_ENV_FILE_ROOT) if _ENV_FILE_ROOT.exists() else (str(_ENV_FILE_LOCAL) if _ENV_FILE_LOCAL else ".env")

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        # Look for .env in project root first, then current directory
        # This allows .env to be in root while running from backend/
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "ZATCA Compliance API"
    app_version: str = "1.0.0"
    debug: bool = False
    # Docs: None = derive from environment_name (local/dev -> True, prod -> False)
    enable_docs: Optional[bool] = None
    # Restrict /docs and /openapi.json to localhost only (recommended for SaaS)
    docs_localhost_only: bool = True
    environment_name: str = "local"  # local, dev, production (use ENVIRONMENT_NAME in .env)
    
    # API Security
    api_key_header: str = "X-API-Key"
    api_keys: str = ""  # Comma-separated list of valid API keys
    
    # Environment
    environment: Environment = Environment.SANDBOX
    
    # ZATCA Environment (Single Source of Truth)
    # CRITICAL: This determines which ZATCA client to use (SANDBOX or PRODUCTION)
    # Set via ZATCA_ENV environment variable: "SANDBOX" or "PRODUCTION"
    zatca_env: str = "SANDBOX"
    
    # ZATCA Integration
    zatca_sandbox_base_url: str = "https://gw-apic-gov.gazt.gov.sa/e-invoicing/developer-portal"
    zatca_production_base_url: str = "https://gw-apic-gov.gazt.gov.sa/e-invoicing/core"
    zatca_timeout: int = 30
    zatca_max_retries: int = 3  # Maximum number of retry attempts
    zatca_retry_delay: float = 1.0  # Initial retry delay in seconds (exponential backoff)
    
    # ZATCA OAuth (Client-Credentials Flow)
    zatca_sandbox_client_id: Optional[str] = None
    zatca_sandbox_client_secret: Optional[str] = None
    zatca_production_client_id: Optional[str] = None
    zatca_production_client_secret: Optional[str] = None
    zatca_oauth_timeout: float = 10.0  # OAuth token request timeout in seconds
    
    # Cryptographic
    signing_key_path: Optional[str] = None
    signing_certificate_path: Optional[str] = None
    
    # AI Services
    enable_ai_explanation: bool = False  # Global AI toggle (enterprise-safe default: disabled)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_base_url: Optional[str] = None  # Optional custom base URL
    
    # OpenRouter (Primary AI Provider)
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "openai/gpt-4o-mini"
    openrouter_timeout: int = 60  # Timeout in seconds
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Phase 9: Internal operations
    internal_secret_key: Optional[str] = None  # Required for internal endpoints
    
    # Phase 9: Data retention policy
    retention_days: int = 180  # Default: 180 days (6 months)
    retention_cleanup_mode: str = "anonymize"  # "anonymize" or "purge"
    
    # Database Configuration
    # PostgreSQL for production/dev, SQLite only for tests
    database_url: Optional[str] = None  # Defaults to PostgreSQL if not set
    async_database_url: Optional[str] = None  # For async operations (optional)
    
    def get_database_url(self) -> str:
        """
        Returns the database URL.
        
        Priority:
        1. DATABASE_URL environment variable (if set)
        2. PostgreSQL default (if not in test mode)
        3. SQLite fallback (only for tests)
        
        Tests should use SQLite in-memory via pytest fixtures, not this setting.
        """
        # If explicitly set, use it
        if self.database_url:
            return self.database_url
        
        # Check if we're in test mode (pytest sets this)
        import sys
        if "pytest" in sys.modules:
            # Tests use their own in-memory SQLite via fixtures
            # This should not be reached, but provide fallback
            return "sqlite:///:memory:"
        
        # Default to PostgreSQL for dev/prod
        # User must set DATABASE_URL environment variable
        raise ValueError(
            "DATABASE_URL must be set. "
            "Example: postgresql+psycopg2://user:password@localhost:5432/zatca_ai"
        )
    
    @property
    def zatca_base_url(self) -> str:
        """Returns the appropriate ZATCA base URL based on environment."""
        if self.environment == Environment.PRODUCTION:
            return self.zatca_production_base_url
        return self.zatca_sandbox_base_url
    
    @property
    def valid_api_keys(self) -> set[str]:
        """Returns a set of valid API keys."""
        if not self.api_keys:
            return set()
        return {key.strip() for key in self.api_keys.split(",") if key.strip()}
    
    @property
    def zatca_environment(self) -> str:
        """
        Returns ZATCA environment (SANDBOX or PRODUCTION).
        
        CRITICAL: This is the single source of truth for ZATCA client routing.
        """
        env_upper = self.zatca_env.upper()
        if env_upper not in ("SANDBOX", "PRODUCTION"):
            raise ValueError(
                f"Invalid ZATCA_ENV value: {self.zatca_env}. "
                f"Must be 'SANDBOX' or 'PRODUCTION' (case-insensitive)."
            )
        return env_upper
    
    @field_validator("enable_docs", mode="before")
    @classmethod
    def empty_enable_docs_to_none(cls, v: object) -> Optional[bool]:
        """Coerce empty string from env to None so validator can derive from ENVIRONMENT_NAME."""
        if v == "" or v is None:
            return None
        return v

    @model_validator(mode="after")
    def set_enable_docs_from_environment(self) -> "Settings":
        """Derive enable_docs from environment_name when not explicitly set (ENABLE_DOCS)."""
        if self.enable_docs is None:
            env = (self.environment_name or "").lower()
            object.__setattr__(self, "enable_docs", env in ("local", "dev"))
        return self

    def model_post_init(self, __context) -> None:
        """Validates configuration after initialization."""
        # Validate ZATCA environment (fail fast if invalid)
        try:
            _ = self.zatca_environment  # This will raise if invalid
        except ValueError as e:
            raise ValueError(f"Configuration validation failed: {e}")
        
        if not self.valid_api_keys and self.environment == Environment.PRODUCTION:
            raise ValueError("At least one API key must be configured for production environment")


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Returns application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


settings = get_settings()

