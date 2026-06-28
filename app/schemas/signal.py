"""Signal schemas."""

from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime


class SignalCreate(BaseModel):
    raw_text: str = Field(..., min_length=1, description="Raw message text")
    symbol: Optional[str] = Field(None, max_length=20)
    action: Optional[str] = Field(None, pattern="^(BUY|SELL)$")
    order_type: Optional[str] = Field(None, pattern="^(LIMIT|STOP|MARKET|STOP_LIMIT)$")
    entry_price: Optional[Decimal] = Field(None, decimal_places=8)
    stop_loss: Optional[Decimal] = Field(None, decimal_places=8)
    take_profit: Optional[List[Dict[str, Any]]] = Field(
        None, description="List of {level: int, price: Decimal}"
    )
    channel_id: Optional[int] = None
    confidence: Optional[int] = Field(None, ge=0, le=100)

    @field_validator("take_profit")
    @classmethod
    def validate_take_profit(cls, v: Optional[List[Dict]]) -> Optional[List[Dict]]:
        if v is not None:
            for item in v:
                if "level" not in item or "price" not in item:
                    raise ValueError("Each TP level must have 'level' and 'price'")
                if not isinstance(item["level"], int) or item["level"] < 1:
                    raise ValueError("Level must be positive integer")
        return v


class SignalUpdate(BaseModel):
    raw_text: Optional[str] = Field(None, min_length=1)
    symbol: Optional[str] = Field(None, max_length=20)
    action: Optional[str] = Field(None, pattern="^(BUY|SELL)$")
    order_type: Optional[str] = Field(None, pattern="^(LIMIT|STOP|MARKET|STOP_LIMIT)$")
    entry_price: Optional[Decimal] = Field(None, decimal_places=8)
    stop_loss: Optional[Decimal] = Field(None, decimal_places=8)
    take_profit: Optional[List[Dict[str, Any]]] = None
    channel_id: Optional[int] = None
    status: Optional[str] = Field(None, pattern="^(PENDING|EXECUTED|EXPIRED|CANCELLED)$")
    confidence: Optional[int] = Field(None, ge=0, le=100)


class SignalRead(BaseModel):
    id: int
    raw_text: Optional[str] = None
    symbol: str
    action: str
    order_type: str
    entry_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[List[Dict[str, Any]]] = None
    confidence: int
    status: str
    channel_id: Optional[int] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SignalList(BaseModel):
    items: List[SignalRead]
    total: int
    page: int
    page_size: int