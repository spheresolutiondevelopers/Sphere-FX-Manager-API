"""JWT authentication middleware."""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth import decode_access_token
from app.services.database import AsyncSessionLocal
from app.models import User
from sqlalchemy import select
from typing import Optional


class JWTBearer(HTTPBearer):
    """
    HTTP Bearer token authentication using JWT.
    """

    async def __call__(self, request: Request) -> Optional[dict]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user ID",
            )

        # Optionally verify user still exists and is active
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.id == user_id, User.is_active == True)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                )

        # Attach user_id to request state
        request.state.user_id = user_id
        request.state.user = user  # can be accessed in route handlers
        return payload