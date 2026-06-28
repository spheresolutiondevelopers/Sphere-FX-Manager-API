"""User model."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String(20), default="user")  # admin, user
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    signals = relationship("Signal", back_populates="user")
    backtest_runs = relationship("BacktestRun", back_populates="user")
    live_jobs = relationship("LiveJob", back_populates="user")
    channels = relationship("TelegramChannel", back_populates="user")
    accounts = relationship("MT5Account", back_populates="user")
    licenses = relationship("License", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")