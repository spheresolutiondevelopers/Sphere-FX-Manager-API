"""Live trading endpoints (job enqueuing and status)."""

from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.dependencies import get_db, get_current_user, require_valid_license, require_feature
from app.models import LiveJob, Signal, MT5Account, User
from app.schemas import LiveRouteRequest, LiveJobStatus, LiveJobResult
from app.services.queue_service import enqueue_job, get_job_status, cancel_job
from app.exceptions import NotFoundError, ValidationError, ConflictError
from app.utils.number_helpers import normalize_lot
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/route", response_model=LiveJobStatus, status_code=status.HTTP_202_ACCEPTED)
async def route_signal_to_live(
    request: LiveRouteRequest,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    live_trading_enabled: bool = Depends(require_feature("live_trading")),
    session: AsyncSession = Depends(get_db),
):
    """
    Enqueue a signal for live trading.
    The job will be picked up by the Go Live Worker.
    """
    # Fetch signal
    stmt = select(Signal).where(
        Signal.id == request.signal_id,
        Signal.created_by == current_user.id
    )
    result = await session.execute(stmt)
    signal = result.scalar_one_or_none()
    if not signal:
        raise NotFoundError(f"Signal {request.signal_id} not found or not owned")

    # Fetch account
    stmt = select(MT5Account).where(
        MT5Account.id == request.account_id,
        MT5Account.user_id == current_user.id,
        MT5Account.is_active == True
    )
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundError(f"Account {request.account_id} not found or inactive")

    # Determine lot size: if not provided, calculate from account balance and risk settings
    lot_size = request.lot_size
    if lot_size is None:
        # Use default risk % (e.g., 1% of balance)
        risk_percent = Decimal('1.0')
        if account.balance_cache:
            risk_amount = account.balance_cache * (risk_percent / 100)
            # Calculate stop loss distance in pips
            # Simplified: assume SL is given in signal
            if signal.stop_loss and signal.entry_price:
                pip_distance = abs(signal.entry_price - signal.stop_loss) / Decimal('0.0001')
                # pip value depends on symbol; we'll use a simplified approach
                # For a real implementation, fetch pip value from symbol table
                pip_value = Decimal('0.0001')  # placeholder
                lot_size = risk_amount / (pip_distance * pip_value) if pip_distance > 0 else Decimal('0.01')
            else:
                lot_size = Decimal('0.01')
        else:
            lot_size = Decimal('0.01')
        # Normalize lot size
        lot_size = normalize_lot(lot_size, Decimal('0.01'), Decimal('100.0'))

    # Build payload for the worker
    payload = {
        "signal_id": signal.id,
        "account_id": account.id,
        "symbol": signal.symbol,
        "action": signal.action,
        "order_type": signal.order_type,
        "entry_price": float(signal.entry_price) if signal.entry_price else None,
        "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
        "take_profit": signal.take_profit,
        "lot_size": float(lot_size),
    }

    # Check if a job already exists for this signal and account
    stmt = select(LiveJob).where(
        LiveJob.signal_id == signal.id,
        LiveJob.account_id == account.id,
        LiveJob.status.in_(["PENDING", "CLAIMED"])
    )
    result = await session.execute(stmt)
    existing_job = result.scalar_one_or_none()
    if existing_job:
        raise ConflictError("A pending job already exists for this signal and account")

    # Enqueue job
    job = await enqueue_job(
        session=session,
        signal_id=signal.id,
        account_id=account.id,
        user_id=current_user.id,
        lot_size=lot_size,
        payload=payload,
    )

    logger.info(f"Live job {job.id} enqueued for signal {signal.id} by user {current_user.id}")
    return LiveJobStatus(
        job_id=job.id,
        signal_id=job.signal_id,
        account_id=job.account_id,
        status=job.status,
        lot_size=job.lot_size,
        created_at=job.created_at,
    )


@router.get("/job/{job_id}", response_model=LiveJobStatus)
async def get_job_status_endpoint(
    job_id: str,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Get the status of a live job."""
    job = await get_job_status(session, job_id)
    if not job or job.user_id != current_user.id:
        raise NotFoundError(f"Job {job_id} not found or not owned")
    return LiveJobStatus(
        job_id=job.id,
        signal_id=job.signal_id,
        account_id=job.account_id,
        status=job.status,
        lot_size=job.lot_size,
        result=job.result,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


@router.delete("/job/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job_endpoint(
    job_id: str,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Cancel a pending live job."""
    job = await get_job_status(session, job_id)
    if not job or job.user_id != current_user.id:
        raise NotFoundError(f"Job {job_id} not found or not owned")

    cancelled = await cancel_job(session, job_id)
    if not cancelled:
        raise ConflictError("Job cannot be cancelled (already claimed or completed)")

    logger.info(f"Live job {job_id} cancelled by user {current_user.id}")
    return None