"""Alembic environment with dialect branching for SQL Server vs SQLite."""

import asyncio
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine, text
from alembic import context
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.base import Base
from app.config import settings

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def enable_service_broker(connection):
    """
    Enable Service Broker on the database.
    This must be run outside of an explicit transaction block.
    """
    try:
        # Use execution_options to run this statement in autocommit isolation
        autocommit_conn = connection.execution_options(isolation_level="AUTOCOMMIT")
        autocommit_conn.execute(
            text("ALTER DATABASE CURRENT SET ENABLE_BROKER WITH ROLLBACK IMMEDIATE")
        )
        print("Service Broker enabled successfully")
    except Exception as e:
        error_msg = str(e).lower()
        # Catching expected states or permission blocks on restricted tiers
        if "already enabled" in error_msg or "cannot be enabled" in error_msg:
            print("Service Broker already enabled or cannot be changed on this tier.")
        else:
            raise


def do_run_migrations(connection):
    """Core migration runner."""
    dialect_name = connection.dialect.name
    
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        render_as_batch=(dialect_name == "sqlite"),
    )

    # Enable Service Broker outside the transaction
    if dialect_name == "mssql":
        enable_service_broker(connection)
    elif dialect_name == "sqlite":
        connection.execute(text("PRAGMA foreign_keys=ON"))

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online_sync() -> None:
    """Run migrations in 'online' mode with synchronous connection."""
    # Get URL from environment variable
    database_url = os.getenv("SYNC_DATABASE_URL", settings.SYNC_DATABASE_URL)
    if not database_url:
        raise ValueError("SYNC_DATABASE_URL environment variable is not set")

    # Build engine using the URL directly
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Use sync only (avoid async driver issues on Windows)
    run_migrations_online_sync()