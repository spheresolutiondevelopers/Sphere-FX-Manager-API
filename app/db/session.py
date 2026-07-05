"""Database session factories and engine configuration."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from app.db.base import Base
import os

# ──────────────────────────────────────────────────────────────
# Async Engine (for FastAPI) - using aioodbc
# ──────────────────────────────────────────────────────────────

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_db():
    """
    FastAPI dependency that yields an async database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ──────────────────────────────────────────────────────────────
# Sync Engine (for Alembic and CLI tools) - using pyodbc
# ──────────────────────────────────────────────────────────────

# For Windows, we need to ensure the ODBC driver name is correct
def get_sync_connection_string():
    """Return the correct sync connection string for Windows."""
    url = settings.SYNC_DATABASE_URL
    
    # If using ODBC Driver 18, ensure the driver name is correct
    if "ODBC Driver 18" in url or "ODBC+Driver" in url:
        # Already correct
        return url
    
    # For Windows, explicitly set the driver
    # Replace with your actual driver name
    if "pyodbc" in url:
        # Remove any existing driver parameter and add the correct one
        import re
        # Remove existing driver parameter
        url = re.sub(r'\?driver=[^&]*', '', url)
        url = re.sub(r'&driver=[^&]*', '', url)
        # Add the correct driver
        if '?' in url:
            url += '&driver=ODBC+Driver+18+for+SQL+Server'
        else:
            url += '?driver=ODBC+Driver+18+for+SQL+Server'
    
    return url

sync_engine = create_engine(
    get_sync_connection_string(),
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def get_sync_db():
    """
    Synchronous database session generator (for scripts and Alembic).
    """
    with SyncSessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()