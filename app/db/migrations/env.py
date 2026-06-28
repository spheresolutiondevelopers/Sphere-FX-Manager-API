"""Alembic environment with dialect branching for SQL Server vs SQLite."""

import asyncio
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.base import Base
from app.config import settings

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
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


async def run_migrations_online_async() -> None:
    """Run migrations in 'online' mode with an async connection."""

    # Determine the URL from environment (or fallback)
    database_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    config.set_main_option("sqlalchemy.url", database_url)

    # Create async engine
    connectable = AsyncEngine(
        create_async_engine(
            database_url,
            poolclass=pool.NullPool,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    """
    Synchronous migration runner that uses the async connection's sync proxy.
    This is called via connection.run_sync().
    """
    dialect_name = connection.dialect.name
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        # Branch on dialect: for SQLite, skip SQL Server-specific DDL
        # We handle this via conditional execution in the migration scripts.
        # But we can also pass a flag to the context for extra control.
        render_as_batch=(dialect_name == "sqlite"),
    )

    # ★ KEY FIX: execute dialect-specific setup before migrations
    if dialect_name == "mssql":
        # Ensure Service Broker is enabled (if not already)
        # This is safe to run multiple times
        connection.execute("ALTER DATABASE CURRENT SET ENABLE_BROKER WITH ROLLBACK IMMEDIATE")
    elif dialect_name == "sqlite":
        # Enable foreign key enforcement for SQLite
        connection.execute("PRAGMA foreign_keys=ON")

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online_sync() -> None:
    """Run migrations in 'online' mode with a synchronous connection."""
    database_url = os.getenv("SYNC_DATABASE_URL", settings.SYNC_DATABASE_URL)
    config.set_main_option("sqlalchemy.url", database_url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Use async version if possible, else fallback to sync
    try:
        asyncio.run(run_migrations_online_async())
    except Exception:
        # Fallback to sync (e.g., when running in a script without asyncio)
        run_migrations_online_sync()