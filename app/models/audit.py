"""Audit log model."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT
    entity_type = Column(String(50), nullable=False)  # signal, user, account, etc.
    entity_id = Column(Integer, nullable=True)
    diff = Column(JSON, nullable=True)  # changes made
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    timestamp = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="audit_logs")