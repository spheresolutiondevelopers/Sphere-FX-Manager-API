"""MT5 account management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from cryptography.fernet import Fernet
from app.dependencies import get_db, get_current_user, require_valid_license
from app.models import MT5Account, User
from app.schemas import AccountCreate, AccountUpdate, AccountRead
from app.exceptions import NotFoundError, ConflictError, ValidationError
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Fernet for encryption (key from environment)
fernet = Fernet(settings.FERNET_KEY.encode())


def encrypt_password(password: str) -> str:
    """Encrypt a password using Fernet."""
    return fernet.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """Decrypt a password."""
    return fernet.decrypt(encrypted.encode()).decode()


router = APIRouter()


@router.get("/", response_model=List[AccountRead])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """List all MT5 accounts for the current user."""
    stmt = select(MT5Account).where(MT5Account.user_id == current_user.id)
    result = await session.execute(stmt)
    accounts = result.scalars().all()
    return [AccountRead.model_validate(a) for a in accounts]


@router.get("/{account_id}", response_model=AccountRead)
async def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Get a single MT5 account."""
    stmt = select(MT5Account).where(
        MT5Account.id == account_id,
        MT5Account.user_id == current_user.id
    )
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundError(f"Account {account_id} not found")
    return AccountRead.model_validate(account)


@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Create a new MT5 account."""
    # Check for duplicate login (encrypted)
    encrypted_login = encrypt_password(account_data.login)
    stmt = select(MT5Account).where(
        MT5Account.login == encrypted_login,
        MT5Account.user_id == current_user.id
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise ConflictError("Account with this login already exists for this user")

    account = MT5Account(
        user_id=current_user.id,
        login=encrypt_password(account_data.login),
        password=encrypt_password(account_data.password),
        server=account_data.server,
        is_active=account_data.is_active,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)

    # Return masked login (show only last 4 chars)
    masked_login = "****" + account_data.login[-4:]
    account.login = masked_login
    return AccountRead.model_validate(account)


@router.put("/{account_id}", response_model=AccountRead)
async def update_account(
    account_id: int,
    account_data: AccountUpdate,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Update an MT5 account."""
    stmt = select(MT5Account).where(
        MT5Account.id == account_id,
        MT5Account.user_id == current_user.id
    )
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundError(f"Account {account_id} not found")

    update_data = account_data.model_dump(exclude_unset=True)
    if "login" in update_data:
        update_data["login"] = encrypt_password(update_data["login"])
    if "password" in update_data:
        update_data["password"] = encrypt_password(update_data["password"])

    for key, value in update_data.items():
        setattr(account, key, value)

    await session.commit()
    await session.refresh(account)

    # Mask login
    account.login = "****" + account.login[-4:]
    return AccountRead.model_validate(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    license_valid: bool = Depends(require_valid_license),
    session: AsyncSession = Depends(get_db),
):
    """Delete an MT5 account."""
    stmt = select(MT5Account).where(
        MT5Account.id == account_id,
        MT5Account.user_id == current_user.id
    )
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundError(f"Account {account_id} not found")

    await session.delete(account)
    await session.commit()
    return None