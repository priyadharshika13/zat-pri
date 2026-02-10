"""
Database session management.

Provides database session creation and management.
Handles connection pooling and session lifecycle.
Does not contain database models or CRUD operations.

CRITICAL: Tests use their own in-memory SQLite engines via pytest fixtures.
This module is for production/dev runtime only.
"""

from typing import Generator, Optional
import os

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings
from app.utils.db_host import resolve_db_host, normalize_database_url

settings = get_settings()

# Global engine - created lazily on first use
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_database_url() -> str:
    """
    Gets the database URL from environment or settings.
    
    Priority:
    1. Settings database_url (from .env file via pydantic-settings)
    2. DATABASE_URL environment variable (auto-normalized for host)
    3. Auto-resolved URL based on runtime (docker vs host)
    4. Raise error (must be set for non-test environments)
    """
    # Check settings first (pydantic-settings loads .env into Settings instance)
    # This is the most reliable way to get .env values
    if settings.database_url:
        return normalize_database_url(settings.database_url)
    
    # Check environment variable (may be set directly, not from .env)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Normalize host if needed (postgres <-> localhost)
        return normalize_database_url(db_url)
    
    # Auto-resolve based on runtime environment
    # Pass settings instance so it can read from .env if needed
    try:
        resolved_url = resolve_db_host(settings)
        return resolved_url
    except Exception:
        # If auto-resolution fails, continue to error
        pass
    
    # Check if we're in test mode
    import sys
    if "pytest" in sys.modules:
        # Tests should use their own fixtures, but provide fallback
        return "sqlite:///:memory:"
    
    # Must be set for production/dev
    raise ValueError(
        "DATABASE_URL must be set as environment variable or in settings. "
        "Example: postgresql+psycopg2://user:password@localhost:5432/zatca_ai"
    )


def get_engine() -> Engine:
    """
    Creates or returns the database engine.
    
    Uses PostgreSQL for production/dev, SQLite only as fallback for tests.
    """
    global _engine
    
    if _engine is None:
        db_url = get_database_url()
        
        # Determine if PostgreSQL or SQLite
        is_postgresql = db_url.startswith("postgresql")
        is_sqlite = db_url.startswith("sqlite")
        
        # Configure engine based on database type
        if is_postgresql:
            # PostgreSQL configuration
            engine_kwargs = {
                "url": db_url,
                "poolclass": QueuePool,
                "pool_size": 5,
                "max_overflow": 10,
                "pool_pre_ping": True,  # Verify connections before using
                "echo": settings.debug,  # Log SQL queries in debug mode
            }
        elif is_sqlite:
            # SQLite configuration (only for tests/fallback)
            engine_kwargs = {
                "url": db_url,
                "connect_args": {"check_same_thread": False},
                "poolclass": NullPool,  # SQLite doesn't need connection pooling
                "echo": settings.debug,
            }
        else:
            raise ValueError(f"Unsupported database URL format: {db_url}")
        
        _engine = create_engine(**engine_kwargs)
    
    return _engine


def get_session_local() -> sessionmaker:
    """Gets or creates the SessionLocal factory."""
    global _SessionLocal
    
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return _SessionLocal


# For backward compatibility
def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.
    
    Yields:
        Database session
    """
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Expose SessionLocal for backward compatibility (used in main.py, etc.)
# Use a lazy property pattern - initialized on first access
class _SessionLocalProxy:
    """Lazy proxy for SessionLocal that initializes on first access."""
    def __call__(self, *args, **kwargs):
        """Call the sessionmaker to create a session."""
        return get_session_local()(*args, **kwargs)
    
    def __getattr__(self, name):
        """Delegate attribute access to the actual sessionmaker."""
        return getattr(get_session_local(), name)

SessionLocal = _SessionLocalProxy()

