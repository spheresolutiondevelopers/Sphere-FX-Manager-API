"""Job queue service using MS SQL Server as the queue."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from app.models import LiveJob, Signal, MT5Account
from decimal import Decimal
import uuid


async def enqueue_job(
    session: AsyncSession,
    signal_id: int,
    account_id: int,
    user_id: int,
    lot_size: Decimal,
    payload: Dict[str, Any],
) -> LiveJob:
    """Enqueue a new live trading job."""
    job = LiveJob(
        id=str(uuid.uuid4()),
        signal_id=signal_id,
        account_id=account_id,
        user_id=user_id,
        lot_size=lot_size,
        payload=payload,
        status="PENDING",
        created_at=datetime.utcnow(),
    )
    session.add(job)
    await session.flush()
    return job


async def get_job_status(
    session: AsyncSession,
    job_id: str,
) -> Optional[LiveJob]:
    """Retrieve a job by ID."""
    query = select(LiveJob).where(LiveJob.id == job_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def cancel_job(
    session: AsyncSession,
    job_id: str,
) -> bool:
    """Cancel a PENDING job."""
    query = update(LiveJob).where(
        LiveJob.id == job_id,
        LiveJob.status == "PENDING"
    ).values(
        status="CANCELLED",
        finished_at=datetime.utcnow(),
    )
    result = await session.execute(query)
    await session.flush()
    return result.rowcount > 0


async def claim_job(
    session: AsyncSession,
    worker_id: str,
) -> Optional[LiveJob]:
    """
    Claim the next PENDING job using ROWLOCK+READPAST.
    Returns the claimed job or None.
    """
    # Use raw SQL for precise locking semantics
    raw_sql = text("""
        SELECT TOP 1 *
        FROM live_jobs WITH (UPDLOCK, READPAST)
        WHERE status = 'PENDING'
        ORDER BY created_at ASC
    """)
    result = await session.execute(raw_sql)
    row = result.fetchone()
    if not row:
        return None

    job = LiveJob(**row._mapping)  # convert to LiveJob instance

    # Mark as claimed
    job.status = "CLAIMED"
    job.claimed_at = datetime.utcnow()
    job.started_at = datetime.utcnow()
    await session.flush()
    return job


async def complete_job(
    session: AsyncSession,
    job_id: str,
    status: str,  # SUCCESS, FAILED
    result: Dict[str, Any],
) -> bool:
    """Mark a job as completed."""
    query = update(LiveJob).where(
        LiveJob.id == job_id,
        LiveJob.status == "CLAIMED"
    ).values(
        status=status,
        result=result,
        finished_at=datetime.utcnow(),
    )
    result = await session.execute(query)
    await session.flush()
    return result.rowcount > 0