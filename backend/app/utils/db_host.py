"""
Database host resolution utility.

Automatically detects the correct PostgreSQL host based on runtime environment:
- If running inside Docker: use 'postgres' (service name)
- If running on host (Codespaces/local): use 'localhost'
"""

import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from typing import Optional


def is_running_in_docker() -> bool:
    """
    Detects if the application is running inside a Docker container.
    
    Returns:
        True if running in Docker, False otherwise
    """
    # Check for /.dockerenv file (most reliable)
    if Path("/.dockerenv").exists():
        return True
    
    # Check for DOCKER_CONTAINER environment variable
    if os.getenv("DOCKER_CONTAINER", "").lower() in ("true", "1", "yes"):
        return True
    
    # Check cgroup (Linux containers)
    try:
        with open("/proc/self/cgroup", "r") as f:
            content = f.read()
            if "docker" in content or "containerd" in content:
                return True
    except (FileNotFoundError, IOError):
        pass
    
    return False


def resolve_db_host(settings: Optional[object] = None) -> str:
    """
    Resolves the correct PostgreSQL host and constructs DATABASE_URL.
    
    Reads credentials from environment variables (loaded from .env by pydantic-settings):
    - DATABASE_URL (highest priority, if set)
    - POSTGRES_USER (default: zatca)
    - POSTGRES_PASSWORD (default: zatca123)
    - POSTGRES_DB (default: zatca_ai)
    - POSTGRES_HOST (optional, auto-detected if not set)
    
    Args:
        settings: Optional Settings instance to read values from (avoids circular import)
    
    Returns:
        Complete DATABASE_URL string
    """
    # If DATABASE_URL is already set in environment, use it as-is (respect override)
    # This works because pydantic-settings loads .env into os.environ when Settings is instantiated
    existing_url = os.getenv("DATABASE_URL")
    if existing_url:
        return existing_url
    
    # Try to get from Settings instance if provided (reads from .env)
    if settings and hasattr(settings, 'database_url') and settings.database_url:
        return settings.database_url
    
    # Read credentials from environment variables
    # pydantic-settings loads .env into os.environ, so os.getenv() should work
    # But if .env wasn't loaded yet, use defaults for E2E/docker-compose
    db_user = os.getenv("POSTGRES_USER") or os.getenv("DATABASE_USER") or "zatca"
    db_password = os.getenv("POSTGRES_PASSWORD") or os.getenv("DATABASE_PASSWORD") or "zatca123"
    db_name = os.getenv("POSTGRES_DB") or os.getenv("DATABASE_NAME") or "zatca_ai"
    
    # Auto-detect host if not explicitly set
    db_host = os.getenv("POSTGRES_HOST") or os.getenv("DATABASE_HOST")
    if not db_host:
        if is_running_in_docker():
            db_host = "postgres"  # Docker service name
        else:
            db_host = "localhost"  # Host machine (Codespaces/local)
    
    # Construct DATABASE_URL
    return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:5432/{db_name}"


def normalize_database_url(db_url: str) -> str:
    """
    Normalizes a DATABASE_URL by ensuring correct host based on runtime.
    
    If the URL contains 'postgres' hostname but we're running on host,
    replace it with 'localhost'. If URL contains 'localhost' but we're
    in docker, replace with 'postgres'.
    
    Args:
        db_url: Original database URL
    
    Returns:
        Normalized database URL with correct host
    """
    if not db_url or not db_url.startswith("postgresql"):
        return db_url
    
    parsed = urlparse(db_url)
    current_host = parsed.hostname
    
    # Determine correct host
    if is_running_in_docker():
        correct_host = "postgres"
    else:
        correct_host = "localhost"
    
    # Only modify if host needs to change
    if current_host != correct_host:
        # Replace hostname in URL
        netloc = parsed.netloc.replace(current_host, correct_host)
        parsed = parsed._replace(netloc=netloc)
        return urlunparse(parsed)
    
    return db_url

