#!/usr/bin/env python
"""One-time database initialisation script."""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import logging
import bcrypt  # <-- ADD THIS

from sqlalchemy import text, select

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.db.session import sync_engine, SyncSessionLocal
from app.models import User, License, Symbol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_database_if_not_exists():
    """Verify database connection."""
    try:
        with sync_engine.connect() as conn:
            result = conn.execute(text("SELECT DB_NAME()"))
            db_name = result.scalar()
            logger.info(f"Connected to database: {db_name}")
    except Exception as e:
        logger.error(f"Could not connect to database: {e}")
        raise


def seed_default_data():
    """Seed default data if tables are empty."""
    with SyncSessionLocal() as session:
        # Check if any users exist
        stmt = select(User).limit(1)
        result = session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.info("Seeding default admin user...")

            # Generate bcrypt hash directly (same format Passlib uses)
            # Use a fixed salt or generate new one
            hashed_password = bcrypt.hashpw(
                b"admin123",
                bcrypt.gensalt()
            ).decode('utf-8')

            admin = User(
                email="admin@spherefx.com",
                hashed_password=hashed_password,
                is_active=True,
                role="admin",
            )
            session.add(admin)
            session.flush()

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

            session.commit()
            logger.info("✅ Default data seeded successfully")
            logger.warning("⚠️  Default admin credentials: admin@spherefx.com / admin123 – CHANGE THIS!")
        else:
            logger.info("Default data already exists; skipping seed.")


def main():
    logger.info("Starting database initialization...")
    create_database_if_not_exists()
    seed_default_data()
    logger.info("✅ Database initialization complete!")


if __name__ == "__main__":
    main()