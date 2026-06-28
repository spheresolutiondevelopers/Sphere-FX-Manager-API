"""License enforcement middleware."""

from fastapi import Request, HTTPException, status
from app.services.license import validate_license_key
from app.config import settings
from app.services.database import AsyncSessionLocal
from app.models import License
from sqlalchemy import select
from datetime import datetime


async def require_valid_license(request: Request):
    """
    Middleware to enforce that a valid, non-expired license exists.
    Must be called after authentication (to know user_id).
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required before license check",
        )

    async with AsyncSessionLocal() as session:
        stmt = select(License).where(
            License.user_id == user_id,
            License.is_active == True,
            License.expires_at > datetime.utcnow()
        )
        result = await session.execute(stmt)
        license_record = result.scalar_one_or_none()
        if not license_record:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Valid license not found or expired",
            )

        # Optionally verify the license key signature if stored as hash
        # For simplicity, we assume the license record is already validated.
        # In production, also verify the ED25519 signature here.

        # Attach license features to request state
        # We'll rely on the license record's features column
        request.state.license_features = license_record.features
        request.state.license = license_record