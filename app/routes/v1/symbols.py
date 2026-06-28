"""Symbol management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.dependencies import get_db, get_current_user, require_valid_license
from app.models import Symbol, User
from app.schemas import SymbolCreate, SymbolUpdate, SymbolRead
from app.exceptions import NotFoundError, ConflictError
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[SymbolRead])
async def list_symbols(
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """List all symbols."""
    stmt = select(Symbol).where(Symbol.is_active == True)
    result = await session.execute(stmt)
    symbols = result.scalars().all()
    return [SymbolRead.model_validate(s) for s in symbols]


@router.get("/{symbol_id}", response_model=SymbolRead)
async def get_symbol(
    symbol_id: int,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Get a single symbol."""
    stmt = select(Symbol).where(Symbol.id == symbol_id)
    result = await session.execute(stmt)
    symbol = result.scalar_one_or_none()
    if not symbol:
        raise NotFoundError(f"Symbol {symbol_id} not found")
    return SymbolRead.model_validate(symbol)


@router.post("/", response_model=SymbolRead, status_code=status.HTTP_201_CREATED)
async def create_symbol(
    symbol_data: SymbolCreate,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Create a new symbol."""
    # Check for duplicate name
    stmt = select(Symbol).where(Symbol.name == symbol_data.name)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise ConflictError(f"Symbol {symbol_data.name} already exists")

    symbol = Symbol(**symbol_data.model_dump())
    session.add(symbol)
    await session.commit()
    await session.refresh(symbol)
    return SymbolRead.model_validate(symbol)


@router.put("/{symbol_id}", response_model=SymbolRead)
async def update_symbol(
    symbol_id: int,
    symbol_data: SymbolUpdate,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Update a symbol."""
    stmt = select(Symbol).where(Symbol.id == symbol_id)
    result = await session.execute(stmt)
    symbol = result.scalar_one_or_none()
    if not symbol:
        raise NotFoundError(f"Symbol {symbol_id} not found")

    update_data = symbol_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(symbol, key, value)

    await session.commit()
    await session.refresh(symbol)
    return SymbolRead.model_validate(symbol)


@router.delete("/{symbol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_symbol(
    symbol_id: int,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Delete a symbol."""
    stmt = select(Symbol).where(Symbol.id == symbol_id)
    result = await session.execute(stmt)
    symbol = result.scalar_one_or_none()
    if not symbol:
        raise NotFoundError(f"Symbol {symbol_id} not found")

    await session.delete(symbol)
    await session.commit()
    return None