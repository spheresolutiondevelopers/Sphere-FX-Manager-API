"""Live trading models (job queue, orders, positions)."""

from sqlalchemy import (
    Column, Integer, String, DECIMAL, DateTime, ForeignKey,
    JSON, Text, func, UniqueConstraint, Boolean
)
from sqlalchemy.orm import relationship
from app.db.base import Base
from decimal import Decimal
import uuid


class LiveJob(Base):
    __tablename__ = "live_jobs"
    __table_args__ = (
        UniqueConstraint("signal_id", "account_id", name="uq_job_signal_account"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("mt5_accounts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lot_size = Column(DECIMAL(10, 4), nullable=False)
    status = Column(String(20), default="PENDING")  # PENDING, CLAIMED, SUCCESS, FAILED
    payload = Column(JSON, nullable=False)  # full signal details for execution
    result = Column(JSON, nullable=True)  # execution result (ticket, fill_price, etc.)
    claimed_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    signal = relationship("Signal", back_populates="live_jobs")
    account = relationship("MT5Account", back_populates="live_jobs")
    user = relationship("User", back_populates="live_jobs")
    orders = relationship("LiveOrder", back_populates="job")
    positions = relationship("LivePosition", back_populates="job")


class LiveOrder(Base):
    __tablename__ = "live_orders"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), ForeignKey("live_jobs.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("mt5_accounts.id"), nullable=False)
    broker_order_id = Column(String(50), nullable=True)
    symbol = Column(String(20), nullable=False)
    action = Column(String(4), nullable=False)
    order_type = Column(String(20), nullable=False)  # MARKET, LIMIT, STOP
    requested_price = Column(DECIMAL(20, 8), nullable=False)
    filled_price = Column(DECIMAL(20, 8), nullable=True)
    lot_size = Column(DECIMAL(10, 4), nullable=False)
    slippage_bps = Column(DECIMAL(10, 2), nullable=True)
    status = Column(String(20), default="PENDING")  # PENDING, FILLED, CANCELLED, REJECTED
    created_at = Column(DateTime, server_default=func.now())
    filled_at = Column(DateTime, nullable=True)

    # Relationships
    job = relationship("LiveJob", back_populates="orders")
    account = relationship("MT5Account", back_populates="live_orders")
    positions = relationship("LivePosition", back_populates="order")


class LivePosition(Base):
    __tablename__ = "live_positions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), ForeignKey("live_jobs.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("live_orders.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("mt5_accounts.id"), nullable=False)
    broker_position_id = Column(String(50), nullable=True)
    symbol = Column(String(20), nullable=False)
    action = Column(String(4), nullable=False)
    entry_price = Column(DECIMAL(20, 8), nullable=False)
    current_price = Column(DECIMAL(20, 8), nullable=True)
    lot_size = Column(DECIMAL(10, 4), nullable=False)
    stop_loss = Column(DECIMAL(20, 8), nullable=True)
    take_profit = Column(JSON, nullable=True)  # array of levels
    remaining_lots = Column(DECIMAL(10, 4), nullable=True)
    status = Column(String(20), default="OPEN")  # OPEN, CLOSED, PARTIAL
    pnl = Column(DECIMAL(12, 2), nullable=True)
    opened_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=True)
    close_reason = Column(String(50), nullable=True)

    # Relationships
    job = relationship("LiveJob", back_populates="positions")
    order = relationship("LiveOrder", back_populates="positions")
    account = relationship("MT5Account", back_populates="live_positions")