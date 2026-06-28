"""MT5 account schemas."""

from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
from datetime import datetime


class AccountCreate(BaseModel):
    login: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)
    server: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True


class AccountUpdate(BaseModel):
    login: Optional[str] = Field(None, min_length=1, max_length=50)
    password: Optional[str] = Field(None, min_length=1)
    server: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    balance_cache: Optional[Decimal] = Field(None, decimal_places=2)
    equity_cache: Optional[Decimal] = Field(None, decimal_places=2)
    last_sync: Optional[datetime] = None


class AccountRead(BaseModel):
    id: int
    login: str  # will be masked in response
    server: str
    is_active: bool
    balance_cache: Optional[Decimal] = None
    equity_cache: Optional[Decimal] = None
    last_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True