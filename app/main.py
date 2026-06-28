"""FastAPI application factory and entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.exceptions import register_exception_handlers
from app.middleware.rate_limit import rate_limit_middleware
from app.metrics import init_metrics, get_metrics
from app.services.extraction_grpc import init_extractor_client, close_extractor_client
from app.services.backtest_grpc import init_backtester_client, close_backtester_client
from app.routes.v1 import router as v1_router
from app.websocket import backtest_logs_websocket, live_updates_websocket
from app.dependencies import JWTBearer

# ──────────────────────────────────────────────────────────────
#  Logging
# ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.yaml.logging.level.upper()),
    format=settings.yaml.logging.format,
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
#  Lifespan Manager
# ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # ── Startup ────────────────────────────────────────────────
    logger.info("Starting Sphere FX Manager API...")

    # Initialize Prometheus metrics
    init_metrics()
    logger.info("Metrics initialized")

    # Initialize gRPC clients
    await init_extractor_client()
    logger.info(f"Extractor gRPC client connected to {settings.EXTRACTOR_GRPC_ADDR}")

    await init_backtester_client()
    logger.info(f"Backtester gRPC client connected to {settings.BACKTESTER_GRPC_ADDR}")

    # Warm up database connection
    from app.db.session import async_engine
    async with async_engine.connect() as conn:
        await conn.execute("SELECT 1")
    logger.info("Database connection verified")

    logger.info("Sphere FX Manager API startup complete")
    yield

    # ── Shutdown ────────────────────────────────────────────────
    logger.info("Shutting down Sphere FX Manager API...")

    # Close gRPC clients
    await close_extractor_client()
    await close_backtester_client()
    logger.info("gRPC clients closed")

    # Dispose database engine
    from app.db.session import async_engine
    await async_engine.dispose()
    logger.info("Database engine disposed")

    logger.info("Sphere FX Manager API shutdown complete")


# ──────────────────────────────────────────────────────────────
#  Application Factory
# ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title="Sphere FX Manager API",
        description="Production-grade API for Telegram signal copier and trade execution",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
        expose_headers=settings.CORS_EXPOSE_HEADERS,
        max_age=settings.CORS_MAX_AGE,
    )

    # ── Rate Limiting Middleware ──────────────────────────────
    # Note: We can apply it globally or per-route.
    # For simplicity, we'll apply it globally.
    # But we need to skip certain paths (e.g., /metrics, /health).
    @app.middleware("http")
    async def rate_limit_middleware_wrapper(request: Request, call_next):
        # Skip rate limiting for health and metrics endpoints
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        return await rate_limit_middleware(request, call_next)

    # ── Register Exception Handlers ────────────────────────────
    register_exception_handlers(app)

    # ── Include Routers ────────────────────────────────────────
    app.include_router(v1_router, prefix="/api/v1")

    # ── WebSocket Routes ───────────────────────────────────────
    app.websocket("/ws/backtest/{run_id}")(backtest_logs_websocket)
    app.websocket("/ws/live/{account_id}")(live_updates_websocket)

    # ── Metrics Endpoint ───────────────────────────────────────
    @app.get("/metrics")
    async def metrics_endpoint():
        """Prometheus metrics endpoint."""
        return get_metrics()

    # ── Health Check ──────────────────────────────────────────
    @app.get("/health")
    async def health_check():
        """Liveness and readiness probe."""
        return {"status": "healthy", "service": "sphere-fx-manager-api"}

    # ── Root ───────────────────────────────────────────────────
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "Sphere FX Manager API",
            "version": "1.0.0",
            "docs": "/docs",
            "status": "operational",
        }

    logger.info("FastAPI application configured")
    return app


# ──────────────────────────────────────────────────────────────
#  Application Instance
# ──────────────────────────────────────────────────────────────

app = create_app()


# ──────────────────────────────────────────────────────────────
#  Entry Point (for uvicorn)
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )