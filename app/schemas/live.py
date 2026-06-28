"""Live trading schemas."""

from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime


class LiveRouteRequest(BaseModel):
    signal_id: int
    account_id: int
    lot_size: Optional[Decimal] = Field(None, decimal_places=4)
    # if lot_size is not provided, it will be calculated from risk settings


class LiveJobStatus(BaseModel):
    job_id: str
    signal_id: int
    account_id: int
    status: str  # PENDING, CLAIMED, SUCCESS, FAILED
    lot_size: Decimal
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    finished_at: Optional[datetime] = None


class LiveJobResult(BaseModel):
    job_id: str
    status: str  # SUCCESS, FAILED
    result: Dict[str, Any]  # includes ticket, fill_price, etc.