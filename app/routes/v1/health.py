"""Health check endpoints."""

from fastapi import APIRouter, Depends
from app.dependencies import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/liveness", status_code=200)
async def liveness_check():
    """Liveness probe: returns 200 if the API is responsive."""
    return {"status": "alive"}


@router.get("/readiness", status_code=200)
async def readiness_check(session: AsyncSession = Depends(get_db)):
    """
    Readiness probe: checks database connectivity and gRPC clients.
    """
    try:
        # Check database
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
        db_ok = False

    # Check gRPC clients (optional)
    grpc_ok = True
    try:
        from app.services.extraction_grpc import _extractor_stub
        if _extractor_stub is None:
            grpc_ok = False
    except:
        grpc_ok = False

    try:
        from app.services.backtest_grpc import _backtester_stub
        if _backtester_stub is None:
            grpc_ok = False
    except:
        grpc_ok = False

    if db_ok and grpc_ok:
        return {"status": "ready", "services": {"database": "ok", "grpc": "ok"}}
    else:
        return {"status": "not_ready", "services": {"database": "ok" if db_ok else "error", "grpc": "ok" if grpc_ok else "error"}}