from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, create_engine
from sqlalchemy import pool

from alembic import context

# Import all models to ensure they're registered with Base
from app.db.models import Base
from app.models.tenant import Tenant
from app.models.api_key import ApiKey
from app.models.invoice_log import InvoiceLog
from app.models.invoice import Invoice, InvoiceStatus  # New Invoice model
from app.models.subscription import Plan, Subscription, UsageCounter

# Import Settings to read DATABASE_URL from .env file (same as app)
from app.core.config import get_settings
from app.db.session import get_database_url

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# CRITICAL: Always use DATABASE_URL from environment/.env (same as app runtime)
# This ensures migrations run against the same database as the application
# Use get_database_url() which reads from Settings (loads .env) and handles auto-detection
try:
    database_url = get_database_url()
    # Use attributes dict to bypass configparser interpolation (handles % characters in passwords)
    config.attributes["sqlalchemy.url"] = database_url
    
    # Verify it's PostgreSQL, not SQLite
    if database_url.startswith("sqlite"):
        raise ValueError(
            "ERROR: Alembic detected SQLite database URL. "
            "Migrations must run against PostgreSQL. "
            f"Current DATABASE_URL: {database_url[:50]}... "
            "Please set DATABASE_URL to a PostgreSQL connection string."
        )
except Exception as e:
    # Fail fast if we can't get a valid PostgreSQL URL
    print(f"ERROR: Failed to get database URL for Alembic: {e}", file=sys.stderr)
    print("ERROR: DATABASE_URL must be set to a PostgreSQL connection string.", file=sys.stderr)
    print("ERROR: Example: postgresql+psycopg2://user:password@localhost:5432/zatca_ai", file=sys.stderr)
    sys.exit(1)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Get URL from attributes (set above from DATABASE_URL)
    # This should always be set - we fail fast if it's not
    url = config.attributes.get("sqlalchemy.url")
    if not url:
        raise ValueError(
            "ERROR: Database URL not set. "
            "DATABASE_URL environment variable must be set to a PostgreSQL connection string."
        )
    
    # Verify it's PostgreSQL
    if url.startswith("sqlite"):
        raise ValueError(
            "ERROR: Alembic cannot run migrations against SQLite. "
            "DATABASE_URL must be set to a PostgreSQL connection string."
        )
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get database URL from attributes (set above from DATABASE_URL)
    # This should always be set - we fail fast if it's not
    database_url = config.attributes.get("sqlalchemy.url")
    if not database_url:
        raise ValueError(
            "ERROR: Database URL not set. "
            "DATABASE_URL environment variable must be set to a PostgreSQL connection string."
        )
    
    # Verify it's PostgreSQL
    if database_url.startswith("sqlite"):
        raise ValueError(
            "ERROR: Alembic cannot run migrations against SQLite. "
            "DATABASE_URL must be set to a PostgreSQL connection string."
        )
    
    # Create engine directly from URL
    connectable = create_engine(database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

