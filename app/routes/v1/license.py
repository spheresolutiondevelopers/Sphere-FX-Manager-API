"""License management endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.dependencies import get_db, get_current_user
from app.models import License, User
from app.schemas import LicenseActivate, LicenseStatus
from app.services.license import validate_license_key
from app.exceptions import ValidationError, NotFoundError
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/activate", response_model=LicenseStatus, status_code=status.HTTP_201_CREATED)
async def activate_license(
    license_data: LicenseActivate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Activate a license for the current user.
    Validates the ED25519 signature and stores the license in the DB.
    """
    # Validate license key
    payload = validate_license_key(license_data.license_key)
    if not payload:
        raise ValidationError("Invalid license key or signature")

    # Check if license user_id matches current user (if present in payload)
    if payload.get("user_id") and payload["user_id"] != current_user.id:
        raise ValidationError("License not assigned to this user")

    # Check if license already exists for this user (active)
    stmt = select(License).where(
        License.user_id == current_user.id,
        License.is_active == True
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise ValidationError("License already active for this user")

    # Create license record
    expires_at = datetime.fromisoformat(payload["expires_at"])
    license_record = License(
        license_key_hash=hash(license_data.license_key),  # simplified; use proper hashing
        user_id=current_user.id,
        features=payload.get("features", {}),
        expires_at=expires_at,
        is_active=True,
    )
    session.add(license_record)
    await session.commit()
    await session.refresh(license_record)

    logger.info(f"License activated for user {current_user.id}")

    return LicenseStatus(
        is_active=True,
        features=license_record.features,
        issued_at=license_record.issued_at,
        expires_at=license_record.expires_at,
        remaining_days=(license_record.expires_at - datetime.utcnow()).days,
    )


@router.get("/status", response_model=LicenseStatus)
async def get_license_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Get the current license status for the logged-in user."""
    stmt = select(License).where(
        License.user_id == current_user.id,
        License.is_active == True
    )
    result = await session.execute(stmt)
    license_record = result.scalar_one_or_none()
    if not license_record:
        return LicenseStatus(
            is_active=False,
            features={},
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow(),
            remaining_days=0,
        )

    return LicenseStatus(
        is_active=license_record.is_active,
        features=license_record.features,
        issued_at=license_record.issued_at,
        expires_at=license_record.expires_at,
        remaining_days=(license_record.expires_at - datetime.utcnow()).days,
    )


@router.post("/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_license(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Deactivate the current user's license."""
    stmt = select(License).where(
        License.user_id == current_user.id,
        License.is_active == True
    )
    result = await session.execute(stmt)
    license_record = result.scalar_one_or_none()
    if not license_record:
        raise NotFoundError("No active license found for this user")

    license_record.is_active = False
    await session.commit()
    logger.info(f"License deactivated for user {current_user.id}")
    return None