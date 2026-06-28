"""Symbol model."""

from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, func
from app.db.base import Base
from decimal import Decimal


class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), nullable=False, index=True)  # EURUSD, XAUUSD, etc.
    broker_name = Column(String(50), nullable=False)  # e.g., "ICMarkets", "MT5"
    category = Column(String(20), nullable=False)  # forex, metal, crypto, index
    pip_value = Column(DECIMAL(10, 6), nullable=False)  # value per pip in quote currency
    min_lot = Column(DECIMAL(10, 2), nullable=False)
    max_lot = Column(DECIMAL(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    # No direct relationships; used by signal processing