"""Symbol schemas."""

from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
from datetime import datetime


class SymbolCreate(BaseModel):
    name: str = Field(..., max_length=20)
    broker_name: str = Field(..., max_length=50)
    category: str = Field(..., max_length=20)
    pip_value: Decimal = Field(..., decimal_places=6)
    min_lot: Decimal = Field(..., decimal_places=2)
    max_lot: Decimal = Field(..., decimal_places=2)
    is_active: bool = True


class SymbolUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=20)
    broker_name: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=20)
    pip_value: Optional[Decimal] = Field(None, decimal_places=6)
    min_lot: Optional[Decimal] = Field(None, decimal_places=2)
    max_lot: Optional[Decimal] = Field(None, decimal_places=2)
    is_active: Optional[bool] = None


class SymbolRead(BaseModel):
    id: int
    name: str
    broker_name: str
    category: str
    pip_value: Decimal
    min_lot: Decimal
    max_lot: Decimal
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True