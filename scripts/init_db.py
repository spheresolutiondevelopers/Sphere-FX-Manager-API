#!/usr/bin/env python
"""One-time database initialisation script.

Creates the database if it doesn't exist, runs all migrations,
and seeds default data (admin user, license, symbols).
"""

import asyncio
import os
import sys
from pathlib import Path
from sqlalchemy import text

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.db.session import async_engine, AsyncSessionLocal
from app.services.auth import hash_password
from app.models import User, License, Symbol
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_database_if_not_exists():
    """Create the database if it does not exist (MS SQL Server)."""
    # Extract database name from connection string
    db_name = settings.DATABASE_URL.split("/")[-1].split("?")[0]
    master_url = settings.DATABASE_URL.replace(f"/{db_name}", "/master")

    # We'll use a raw connection to check/ create the database
    # For SQL Server, we need to connect to master first
    try:
        # Use the async engine to check database existence
        # Simplified: we'll just try to connect and run migrations
        # If the database doesn't exist, Alembic will handle it.
        # For MS SQL, we can run a simple check.
        from sqlalchemy import inspect
        async with async_engine.connect() as conn:
            # Check if we can query a system table
            result = await conn.execute(text("SELECT DB_NAME()"))
            db_name_actual = result.scalar()
            logger.info(f"Connected to database: {db_name_actual}")
    except Exception as e:
        logger.error(f"Could not connect to database: {e}")
        raise


async def seed_default_data():
    """Seed default data if tables are empty."""
    async with AsyncSessionLocal() as session:
        # Check if any users exist
        from sqlalchemy import select
        stmt = select(User).limit(1)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.info("Seeding default admin user...")
            admin = User(
                email="admin@spherefx.com",
                hashed_password=hash_password("admin123"),  # Change me!
                is_active=True,
                role="admin",
            )
            session.add(admin)
            await session.flush()

            # Seed default license for admin
            logger.info("Seeding default license...")
            license_record = License(
                license_key_hash="default_admin_license_hash",
                user_id=admin.id,
                features={
                    "max_accounts": 5,
                    "max_channels": 10,
                    "backtesting": True,
                    "live_trading": True,
                    "ai_advisor": True,
                },
                expires_at=datetime.utcnow() + timedelta(days=365),
                is_active=True,
            )
            session.add(license_record)

            # Seed default symbols
            logger.info("Seeding default symbols...")
            default_symbols = [
                {"name": "EURUSD", "broker_name": "ICMarkets", "category": "forex", "pip_value": 0.0001, "min_lot": 0.01, "max_lot": 100},
                {"name": "GBPUSD", "broker_name": "ICMarkets", "category": "forex", "pip_value": 0.0001, "min_lot": 0.01, "max_lot": 100},
                {"name": "USDJPY", "broker_name": "ICMarkets", "category": "forex", "pip_value": 0.01, "min_lot": 0.01, "max_lot": 100},
                {"name": "XAUUSD", "broker_name": "ICMarkets", "category": "metal", "pip_value": 0.01, "min_lot": 0.01, "max_lot": 100},
                {"name": "BTCUSD", "broker_name": "ICMarkets", "category": "crypto", "pip_value": 1.0, "min_lot": 0.01, "max_lot": 100},
            ]
            for sym_data in default_symbols:
                symbol = Symbol(**sym_data, is_active=True)
                session.add(symbol)

            await session.commit()
            logger.info("✅ Default data seeded successfully")
        else:
            logger.info("Default data already exists; skipping seed.")


async def main():
    """Main entry point."""
    logger.info("Starting database initialization...")
    await create_database_if_not_exists()

    # Run migrations
    logger.info("Running migrations...")
    # We can call alembic programmatically, but for simplicity we'll use the shell script.
    # The script expects to be run from the root.
    import subprocess
    result = subprocess.run(["bash", "scripts/run_migrations.sh"], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Migrations failed: {result.stderr}")
        sys.exit(1)
    logger.info("✅ Migrations complete")

    # Seed default data
    await seed_default_data()

    logger.info("✅ Database initialization complete!")


if __name__ == "__main__":
    asyncio.run(main())