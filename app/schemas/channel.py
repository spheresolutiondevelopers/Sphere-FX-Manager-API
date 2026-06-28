"""Telegram channel schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChannelCreate(BaseModel):
    telegram_channel_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True


class ChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    telegram_channel_id: Optional[str] = Field(None, min_length=1, max_length=50)


class ChannelRead(BaseModel):
    id: int
    telegram_channel_id: str
    name: str
    is_active: bool
    added_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True