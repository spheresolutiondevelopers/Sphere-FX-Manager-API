"""Backtest models."""

from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.db.base import Base
from decimal import Decimal


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="PENDING")  # PENDING, RUNNING, DONE, FAILED
    config = Column(JSON, nullable=False)  # parameters used
    result = Column(JSON, nullable=True)  # summary metrics
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="backtest_runs")
    trades = relationship("BacktestTrade", back_populates="backtest_run")


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id = Column(Integer, primary_key=True, index=True)
    backtest_run_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=False)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    symbol = Column(String(20), nullable=False)
    action = Column(String(4), nullable=False)
    entry_price = Column(DECIMAL(20, 8), nullable=False)
    exit_price = Column(DECIMAL(20, 8), nullable=False)
    rr_achieved = Column(DECIMAL(10, 4), nullable=True)  # risk-reward ratio achieved
    outcome = Column(String(20), nullable=False)  # TP_HIT, SL_HIT, OPEN, CANCELLED
    pnl = Column(DECIMAL(12, 2), nullable=True)  # profit/loss in currency

    # Relationships
    backtest_run = relationship("BacktestRun", back_populates="trades")
    signal = relationship("Signal", back_populates="backtest_trades")