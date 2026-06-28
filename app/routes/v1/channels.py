"""Telegram channel management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.dependencies import get_db, get_current_user, require_valid_license
from app.models import TelegramChannel, User
from app.schemas import ChannelCreate, ChannelUpdate, ChannelRead
from app.exceptions import NotFoundError, ConflictError
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[ChannelRead])
async def list_channels(
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """List all channels for the current user."""
    stmt = select(TelegramChannel).where(TelegramChannel.added_by == current_user.id)
    result = await session.execute(stmt)
    channels = result.scalars().all()
    return [ChannelRead.model_validate(c) for c in channels]


@router.get("/{channel_id}", response_model=ChannelRead)
async def get_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Get a single channel."""
    stmt = select(TelegramChannel).where(
        TelegramChannel.id == channel_id,
        TelegramChannel.added_by == current_user.id
    )
    result = await session.execute(stmt)
    channel = result.scalar_one_or_none()
    if not channel:
        raise NotFoundError(f"Channel {channel_id} not found")
    return ChannelRead.model_validate(channel)


@router.post("/", response_model=ChannelRead, status_code=status.HTTP_201_CREATED)
async def create_channel(
    channel_data: ChannelCreate,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Create a new Telegram channel entry."""
    # Check for duplicate telegram_channel_id
    stmt = select(TelegramChannel).where(
        TelegramChannel.telegram_channel_id == channel_data.telegram_channel_id
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise ConflictError("Channel with this telegram_channel_id already exists")

    channel = TelegramChannel(
        telegram_channel_id=channel_data.telegram_channel_id,
        name=channel_data.name,
        is_active=channel_data.is_active,
        added_by=current_user.id,
    )
    session.add(channel)
    await session.commit()
    await session.refresh(channel)
    return ChannelRead.model_validate(channel)


@router.put("/{channel_id}", response_model=ChannelRead)
async def update_channel(
    channel_id: int,
    channel_data: ChannelUpdate,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Update a channel."""
    stmt = select(TelegramChannel).where(
        TelegramChannel.id == channel_id,
        TelegramChannel.added_by == current_user.id
    )
    result = await session.execute(stmt)
    channel = result.scalar_one_or_none()
    if not channel:
        raise NotFoundError(f"Channel {channel_id} not found")

    update_data = channel_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(channel, key, value)

    await session.commit()
    await session.refresh(channel)
    return ChannelRead.model_validate(channel)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Delete a channel."""
    stmt = select(TelegramChannel).where(
        TelegramChannel.id == channel_id,
        TelegramChannel.added_by == current_user.id
    )
    result = await session.execute(stmt)
    channel = result.scalar_one_or_none()
    if not channel:
        raise NotFoundError(f"Channel {channel_id} not found")

    await session.delete(channel)
    await session.commit()
    return None