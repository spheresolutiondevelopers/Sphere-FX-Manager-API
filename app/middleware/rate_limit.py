"""Sliding-window rate limiter using MS SQL Server."""

from fastapi import Request, HTTPException, status
from app.services.database import AsyncSessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta
import time


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limit middleware using MS SQL to track request counts.
    Limits are defined per route in config.
    """
    # Get the client IP or user_id if authenticated
    client_id = request.client.host
    if hasattr(request.state, "user_id"):
        client_id = f"user_{request.state.user_id}"

    # Determine the limit for this path
    # In a real implementation, you'd read limits from config or per-route settings.
    # Here we use a default: 100 requests per minute per client.
    limit = 100
    window_seconds = 60

    # Use SQL to count requests in the last window
    async with AsyncSessionLocal() as session:
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        raw_sql = text("""
            SELECT COUNT(*) FROM rate_limit_log
            WHERE client_id = :client_id
            AND created_at > :cutoff
        """)
        result = await session.execute(raw_sql, {"client_id": client_id, "cutoff": cutoff})
        count = result.scalar()

        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
            )

        # Log this request
        insert_sql = text("""
            INSERT INTO rate_limit_log (client_id, created_at)
            VALUES (:client_id, GETUTCDATE())
        """)
        await session.execute(insert_sql, {"client_id": client_id})
        await session.commit()

    response = await call_next(request)
    return response