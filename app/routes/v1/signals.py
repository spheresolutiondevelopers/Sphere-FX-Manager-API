"""Signal CRUD endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.dependencies import get_db, get_current_user, require_valid_license
from app.models import Signal, User
from app.schemas import SignalCreate, SignalUpdate, SignalRead, SignalList
from app.services.extraction_grpc import extract_signal
from app.exceptions import NotFoundError, ValidationError
from app.utils.validators import validate_signal_consistency
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=SignalList)
async def list_signals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    symbol: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """
    List signals with pagination and optional filters.
    """
    query = select(Signal).where(Signal.created_by == current_user.id)

    if symbol:
        query = query.where(Signal.symbol.ilike(f"%{symbol}%"))
    if action:
        query = query.where(Signal.action == action.upper())
    if status:
        query = query.where(Signal.status == status.upper())
    if start_date:
        query = query.where(Signal.created_at >= start_date)
    if end_date:
        query = query.where(Signal.created_at <= end_date)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    # Order by newest first
    query = query.order_by(Signal.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    items = result.scalars().all()

    return SignalList(
        items=[SignalRead.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{signal_id}", response_model=SignalRead)
async def get_signal(
    signal_id: int,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Get a single signal by ID."""
    stmt = select(Signal).where(
        Signal.id == signal_id,
        Signal.created_by == current_user.id
    )
    result = await session.execute(stmt)
    signal = result.scalar_one_or_none()
    if not signal:
        raise NotFoundError(f"Signal {signal_id} not found")
    return SignalRead.model_validate(signal)


@router.post("/", response_model=SignalRead, status_code=status.HTTP_201_CREATED)
async def create_signal(
    signal_data: SignalCreate,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """
    Create a new signal from raw text (or direct fields) and run extraction.
    If raw_text is provided, extraction is attempted via gRPC.
    """
    # If raw_text is provided, attempt extraction
    if signal_data.raw_text:
        try:
            extract_response = await extract_signal(signal_data.raw_text)
            if extract_response:
                parsed = extract_response.parsed_signal
                # Override fields from extraction
                signal_data.symbol = parsed.symbol or signal_data.symbol
                signal_data.action = parsed.action or signal_data.action
                signal_data.order_type = parsed.order_type or signal_data.order_type
                if parsed.entry_price:
                    signal_data.entry_price = parsed.entry_price
                if parsed.stop_loss:
                    signal_data.stop_loss = parsed.stop_loss
                if parsed.take_profit:
                    signal_data.take_profit = parsed.take_profit
                signal_data.confidence = parsed.confidence or signal_data.confidence
            else:
                logger.warning(f"Extraction failed for raw_text: {signal_data.raw_text[:50]}...")
        except Exception as e:
            logger.error(f"Extraction error: {e}")

    # Validate consistency
    if signal_data.action and signal_data.entry_price:
        errors = validate_signal_consistency(
            action=signal_data.action,
            entry=signal_data.entry_price,
            stop_loss=signal_data.stop_loss,
            take_profit=signal_data.take_profit,
        )
        if errors:
            raise ValidationError("Signal validation failed", {"errors": errors})

    # Create signal
    signal = Signal(
        raw_text=signal_data.raw_text,
        symbol=signal_data.symbol,
        action=signal_data.action,
        order_type=signal_data.order_type or "MARKET",
        entry_price=signal_data.entry_price,
        stop_loss=signal_data.stop_loss,
        take_profit=signal_data.take_profit,
        confidence=signal_data.confidence or 0,
        channel_id=signal_data.channel_id,
        created_by=current_user.id,
        status="PENDING",
    )

    session.add(signal)
    await session.commit()
    await session.refresh(signal)

    logger.info(f"Signal {signal.id} created by user {current_user.id}")
    return SignalRead.model_validate(signal)


@router.put("/{signal_id}", response_model=SignalRead)
async def update_signal(
    signal_id: int,
    signal_data: SignalUpdate,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Update an existing signal."""
    stmt = select(Signal).where(
        Signal.id == signal_id,
        Signal.created_by == current_user.id
    )
    result = await session.execute(stmt)
    signal = result.scalar_one_or_none()
    if not signal:
        raise NotFoundError(f"Signal {signal_id} not found")

    update_data = signal_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(signal, key, value)

    await session.commit()
    await session.refresh(signal)
    return SignalRead.model_validate(signal)


@router.delete("/{signal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_signal(
    signal_id: int,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Delete a signal."""
    stmt = select(Signal).where(
        Signal.id == signal_id,
        Signal.created_by == current_user.id
    )
    result = await session.execute(stmt)
    signal = result.scalar_one_or_none()
    if not signal:
        raise NotFoundError(f"Signal {signal_id} not found")

    await session.delete(signal)
    await session.commit()
    return None