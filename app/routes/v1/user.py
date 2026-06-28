"""User management endpoints (registration, login, profile)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.dependencies import get_db, get_current_user
from app.models import User
from app.schemas import UserCreate, UserUpdate, UserRead, UserLogin, TokenResponse
from app.services.auth import hash_password, verify_password, create_access_token
from app.exceptions import AuthenticationError, ValidationError, ConflictError
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db),
):
    """Register a new user."""
    # Check if email already exists
    stmt = select(User).where(User.email == user_data.email)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise ConflictError("Email already registered")

    # Hash password
    hashed = hash_password(user_data.password)

    user = User(
        email=user_data.email,
        hashed_password=hashed,
        role=user_data.role or "user",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info(f"User registered: {user.email}")
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    session: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT token."""
    stmt = select(User).where(User.email == login_data.email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthenticationError("Invalid email or password")

    if not verify_password(login_data.password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")

    # Create token
    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the current user's profile."""
    return UserRead.model_validate(current_user)


@router.put("/me", response_model=UserRead)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    update_data = user_data.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))

    for key, value in update_data.items():
        setattr(current_user, key, value)

    await session.commit()
    await session.refresh(current_user)
    return UserRead.model_validate(current_user)