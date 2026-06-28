"""Telegram channel model."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class TelegramChannel(Base):
    __tablename__ = "telegram_channels"

    id = Column(Integer, primary_key=True, index=True)
    telegram_channel_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="channels")
    signals = relationship("Signal", back_populates="channel")