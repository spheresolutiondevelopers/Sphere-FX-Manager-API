"""MT5 account model."""

from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base import Base
from decimal import Decimal


class MT5Account(Base):
    __tablename__ = "mt5_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    login = Column(String(50), nullable=False, index=True)  # encrypted
    password = Column(String(255), nullable=False)  # encrypted
    server = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    balance_cache = Column(DECIMAL(12, 2), nullable=True)
    equity_cache = Column(DECIMAL(12, 2), nullable=True)
    last_sync = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="accounts")
    live_jobs = relationship("LiveJob", back_populates="account")
    live_orders = relationship("LiveOrder", back_populates="account")
    live_positions = relationship("LivePosition", back_populates="account")