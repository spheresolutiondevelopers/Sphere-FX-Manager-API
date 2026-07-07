"""API version 1 routers."""

from fastapi import APIRouter
from .v1.signals import router as signals_router
from .v1.backtest import router as backtest_router
from .v1.live import router as live_router
from .v1.channels import router as channels_router
from .v1.symbols import router as symbols_router
from .v1.accounts import router as accounts_router
from .v1.license import router as license_router
from .v1.user import router as user_router
from .v1.webhook import router as webhook_router
from .v1.configuration import router as configuration_router
from .v1.health import router as health_router

router = APIRouter()

router.include_router(signals_router, prefix="/signals", tags=["signals"])
router.include_router(backtest_router, prefix="/backtest", tags=["backtest"])
router.include_router(live_router, prefix="/live", tags=["live"])
router.include_router(channels_router, prefix="/channels", tags=["channels"])
router.include_router(symbols_router, prefix="/symbols", tags=["symbols"])
router.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
router.include_router(license_router, prefix="/license", tags=["license"])
router.include_router(user_router, prefix="/user", tags=["user"])
router.include_router(webhook_router, prefix="/webhook", tags=["webhook"])
router.include_router(configuration_router, prefix="/configuration", tags=["configuration"])
router.include_router(health_router, prefix="/health", tags=["health"])