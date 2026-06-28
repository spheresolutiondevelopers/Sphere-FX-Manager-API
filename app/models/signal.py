"""Signal model."""

from sqlalchemy import (
    Column, Integer, String, DECIMAL, DateTime, ForeignKey,
    JSON, Text, func
)
from sqlalchemy.orm import relationship
from app.db.base import Base
from sqlalchemy.dialects.mssql import NVARCHAR
from decimal import Decimal


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    raw_text = Column(Text, nullable=True)
    symbol = Column(String(20), nullable=False, index=True)
    action = Column(String(4), nullable=False)  # BUY, SELL
    order_type = Column(String(12), nullable=False)  # LIMIT, STOP, MARKET, STOP_LIMIT
    entry_price = Column(DECIMAL(20, 8), nullable=True)
    stop_loss = Column(DECIMAL(20, 8), nullable=True)
    take_profit = Column(JSON, nullable=True)  # array of {level: int, price: Decimal}
    confidence = Column(Integer, default=0)  # 0-100
    status = Column(String(20), default="PENDING")  # PENDING, EXECUTED, EXPIRED, CANCELLED
    channel_id = Column(Integer, ForeignKey("telegram_channels.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="signals")
    channel = relationship("TelegramChannel", back_populates="signals")
    live_jobs = relationship("LiveJob", back_populates="signal")
    backtest_trades = relationship("BacktestTrade", back_populates="signal")