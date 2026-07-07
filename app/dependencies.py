"""FastAPI dependency injection."""

from typing import Optional, Dict, Any, Callable
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from functools import partial

from app.db.session import get_async_db
from app.services.auth import decode_access_token
from app.services.license import validate_license_key, get_license_features
from app.models import User, License
from app.exceptions import AuthenticationError, LicenseError, NotFoundError
from app.config import settings
from sqlalchemy import select
from datetime import datetime


# ──────────────────────────────────────────────────────────────
#  Database Session
# ──────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:
    """
    Dependency that provides an async database session.
    """
    async for session in get_async_db():
        yield session


# ──────────────────────────────────────────────────────────────
#  Current User (Authentication)
# ──────────────────────────────────────────────────────────────

class JWTBearer(HTTPBearer):
    """
    HTTP Bearer token authentication using JWT.
    """

    async def __call__(self, request: Request) -> Dict[str, Any]:
        credentials = await super().__call__(request)
        if not credentials:
            raise AuthenticationError("Invalid authorization token")

        token = credentials.credentials
        payload = decode_access_token(token)
        if not payload:
            raise AuthenticationError("Invalid or expired token")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Token missing user ID")

        # Fetch user from database
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.id == user_id, User.is_active == True)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                raise AuthenticationError("User not found or inactive")

        # Attach to request state
        request.state.user_id = user_id
        request.state.user = user
        return {"user_id": user_id, "user": user}


async def get_current_user(
    request: Request,
    token_data: Dict[str, Any] = Depends(JWTBearer()),
) -> User:
    """
    Dependency that returns the current authenticated user.
    """
    return token_data["user"]


async def get_current_user_id(
    request: Request,
    token_data: Dict[str, Any] = Depends(JWTBearer()),
) -> int:
    """
    Dependency that returns the current user ID.
    """
    return token_data["user_id"]


# ──────────────────────────────────────────────────────────────
#  License Validation
# ──────────────────────────────────────────────────────────────

async def require_valid_license(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> License:
    """
    Dependency that checks for a valid, non-expired license for the current user.
    Raises LicenseError if invalid.
    """
    # Check database for active license
    stmt = select(License).where(
        License.user_id == current_user.id,
        License.is_active == True,
        License.expires_at > datetime.utcnow()
    )
    result = await session.execute(stmt)
    license_record = result.scalar_one_or_none()

    if not license_record:
        # Try validating the license key from environment (first-run)
        if settings.LICENSE_KEY:
            payload = validate_license_key(settings.LICENSE_KEY)
            if payload and payload.get("user_id") == current_user.id:
                # Create a license record if it doesn't exist
                from datetime import timedelta
                expires_at = datetime.fromisoformat(payload.get("expires_at"))
                new_license = License(
                    license_key_hash=hash(settings.LICENSE_KEY),  # simplified; use proper hashing
                    user_id=current_user.id,
                    features=payload.get("features", {}),
                    expires_at=expires_at,
                    is_active=True,
                )
                session.add(new_license)
                await session.commit()
                await session.refresh(new_license)
                return new_license

        raise LicenseError("Valid license not found or expired")

    # Verify the license key signature (optional)
    # Here we trust the database record; in production, also verify the stored hash.

    return license_record


# ──────────────────────────────────────────────────────────────
#  Feature Check Dependency Factory
# ──────────────────────────────────────────────────────────────

def require_feature(feature_name: str) -> Callable:
    """
    Returns a dependency that checks if a specific feature is enabled in the license.
    Usage: `Depends(require_feature("live_trading"))`
    """
    async def dependency(
        license_record: License = Depends(require_valid_license),
    ) -> bool:
        features = license_record.features or {}
        if not features.get(feature_name, False):
            raise LicenseError(f"Feature '{feature_name}' is not enabled in your license")
        return True
    return dependency


# ──────────────────────────────────────────────────────────────
#  Optional License (for public endpoints)
# ──────────────────────────────────────────────────────────────

async def get_optional_license(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Optional[License]:
    """
    Dependency that returns the license if available, otherwise None.
    Used for public endpoints that may or may not require a license.
    """
    # Try to get user from JWT if present
    try:
        token_data = await JWTBearer()(request)
        user_id = token_data["user_id"]
        stmt = select(License).where(
            License.user_id == user_id,
            License.is_active == True,
            License.expires_at > datetime.utcnow()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    except Exception:
        return None