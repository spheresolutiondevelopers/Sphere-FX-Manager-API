"""Backtest schemas."""

from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime


class BacktestRequest(BaseModel):
    signal_ids: List[int] = Field(..., min_items=1, description="List of signal IDs to backtest")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Overrides for RR, TP strategy, spread, etc."
    )


class BacktestResult(BaseModel):
    run_id: int
    total_signals: int
    win_count: int
    loss_count: int
    win_rate: Decimal = Field(..., max_digits=5, decimal_places=2)
    total_rr: Decimal = Field(..., max_digits=12, decimal_places=4)
    profit_factor: Decimal = Field(..., max_digits=6, decimal_places=4)
    max_drawdown: Decimal = Field(..., max_digits=12, decimal_places=4)
    sharpe_ratio: Decimal = Field(..., max_digits=6, decimal_places=4)
    equity_curve: List[Decimal] = Field(default_factory=list)
    trades: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: datetime
    finished_at: Optional[datetime] = None


class BacktestStatus(BaseModel):
    run_id: int
    status: str  # PENDING, RUNNING, DONE, FAILED
    progress: Optional[int] = Field(None, ge=0, le=100)
    logs: Optional[List[str]] = None
    result: Optional[BacktestResult] = None