"""Runtime configuration endpoints (admin only)."""

from fastapi import APIRouter, Depends, status
from app.dependencies import get_current_user
from app.models import User
from app.exceptions import AuthorizationError
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", status_code=status.HTTP_200_OK)
async def get_configuration(
    current_user: User = Depends(get_current_user),
):
    """Get the current runtime configuration."""
    if current_user.role != "admin":
        raise AuthorizationError("Admin access required")
    # Return configuration from settings (YAML + env)
    from app.config import settings
    return {
        "risk_limits": settings.yaml.risk_limits.model_dump(),
        "backtester": settings.yaml.backtester.model_dump(),
        "queue": settings.yaml.queue.model_dump(),
        "pool": settings.yaml.pool.model_dump(),
        "logging": settings.yaml.logging.model_dump(),
        "debug": settings.DEBUG,
    }


@router.put("/", status_code=status.HTTP_200_OK)
async def update_configuration(
    config_data: dict,
    current_user: User = Depends(get_current_user),
):
    """
    Update runtime configuration.
    This would typically write to the YAML file or update an in-memory store.
    For production, we'd implement a persistent config store (DB or file).
    """
    if current_user.role != "admin":
        raise AuthorizationError("Admin access required")

    # Here we would update the configuration store.
    # For simplicity, we just log and return success.
    logger.info(f"Configuration updated by admin {current_user.id}: {config_data}")

    return {"status": "updated", "message": "Configuration updated successfully (mock)"}