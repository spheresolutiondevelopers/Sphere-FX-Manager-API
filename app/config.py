"""Configuration management using Pydantic Settings with YAML support."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
import yaml
import os
from pathlib import Path

# ──────────────────────────────────────────────────────────────
#  YAML Config Models (mirrors config/config.yaml)
# ──────────────────────────────────────────────────────────────

class RiskLimitsConfig(BaseModel):
    max_lot: float = Field(100.0, description="Maximum lot size per trade")
    min_lot: float = Field(0.01, description="Minimum lot size per trade")
    max_daily_drawdown_percent: float = Field(5.0, description="Maximum daily drawdown percentage")
    min_rr_ratio: float = Field(1.5, description="Minimum risk-reward ratio required")
    max_positions: int = Field(10, description="Maximum concurrent open positions")


class BacktesterConfig(BaseModel):
    default_rr: float = Field(2.0, description="Default risk-reward ratio")
    default_spread_pips: float = Field(1.5, description="Default spread in pips")
    default_commission: float = Field(3.5, description="Default commission per lot in USD")
    min_data_points: int = Field(100, description="Minimum historical data points required")


class QueueConfig(BaseModel):
    poll_interval_seconds: int = Field(2, description="How often the Live Worker polls the queue")
    max_claim_attempts: int = Field(3, description="Maximum attempts before marking job as failed")


class PoolConfig(BaseModel):
    async_pool_size: int = Field(20, description="Async connection pool size")
    async_max_overflow: int = Field(10, description="Async max overflow connections")
    sync_pool_size: int = Field(5, description="Sync connection pool size")


class LoggingConfig(BaseModel):
    level: str = Field("INFO", description="Log level")
    format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class AppYamlConfig(BaseModel):
    risk_limits: RiskLimitsConfig = Field(default_factory=RiskLimitsConfig)
    backtester: BacktesterConfig = Field(default_factory=BacktesterConfig)
    queue: QueueConfig = Field(default_factory=QueueConfig)
    pool: PoolConfig = Field(default_factory=PoolConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


# ──────────────────────────────────────────────────────────────
#  Environment Settings (loaded from .env)
# ──────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    # ─── Database ──────────────────────────────────────────────
    DATABASE_URL: str = Field(..., description="Async SQLAlchemy connection string")
    SYNC_DATABASE_URL: Optional[str] = Field(None, description="Sync connection string for Alembic")
    DB_POOL_SIZE: int = Field(20, description="Connection pool size")
    DB_MAX_OVERFLOW: int = Field(10, description="Max overflow connections")

    # ─── gRPC ──────────────────────────────────────────────────
    EXTRACTOR_GRPC_ADDR: str = Field("localhost:50051", description="Go Extractor gRPC address")
    BACKTESTER_GRPC_ADDR: str = Field("localhost:50052", description="Go Backtester gRPC address")

    # ─── MT5 Bridge ────────────────────────────────────────────
    MT5_BRIDGE_URL: str = Field("http://localhost:8081", description="MT5 Bridge HTTP endpoint")

    # ─── Authentication ────────────────────────────────────────
    JWT_SECRET: str = Field(..., description="JWT signing secret (min 32 characters)")
    JWT_ALGORITHM: str = Field("HS256", description="JWT signing algorithm")
    JWT_EXPIRATION_MINUTES: int = Field(60, description="Token expiry in minutes")

    # ─── License ──────────────────────────────────────────────
    LICENSE_KEY: Optional[str] = Field(None, description="ED25519 signed license key")
    LICENSE_PUBLIC_KEY: str = Field(..., description="Base64 encoded ED25519 public key")

    # ─── Telegram ──────────────────────────────────────────────
    TELEGRAM_API_ID: Optional[int] = Field(None, description="Telegram API ID")
    TELEGRAM_API_HASH: Optional[str] = Field(None, description="Telegram API Hash")
    HMAC_SECRET: Optional[str] = Field(None, description="HMAC secret for webhook verification")

    # ─── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = Field(["*"], description="Allowed CORS origins")
    CORS_METHODS: List[str] = Field(["*"], description="Allowed CORS methods")
    CORS_HEADERS: List[str] = Field(["*"], description="Allowed CORS headers")
    CORS_EXPOSE_HEADERS: List[str] = Field([], description="Exposed CORS headers")
    CORS_MAX_AGE: int = Field(600, description="CORS preflight max age")

    # ─── Debug ──────────────────────────────────────────────────
    DEBUG: bool = Field(False, description="Enable debug mode")

    # ─── YAML Config Path ──────────────────────────────────────
    CONFIG_YAML_PATH: str = Field("config/config.yaml", description="Path to YAML configuration")

    # ─── Load YAML config at runtime ──────────────────────────
    _yaml_config: Optional[AppYamlConfig] = None

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    @field_validator("SYNC_DATABASE_URL", mode="before")
    @classmethod
    def default_sync_url(cls, v: Optional[str], info) -> str:
        if v is None:
            # Derive sync URL from async URL by replacing the async driver
            async_url = info.data.get("DATABASE_URL", "")
            if async_url.startswith("mssql+async"):
                return async_url.replace("mssql+async", "mssql")
            if async_url.startswith("postgresql+async"):
                return async_url.replace("postgresql+async", "postgresql")
            if async_url.startswith("sqlite+async"):
                return async_url.replace("sqlite+async", "sqlite")
            return async_url
        return v

    def load_yaml_config(self) -> AppYamlConfig:
        """
        Load and parse the YAML configuration file.
        """
        if self._yaml_config is not None:
            return self._yaml_config

        yaml_path = Path(self.CONFIG_YAML_PATH)
        if not yaml_path.exists():
            # Use defaults
            self._yaml_config = AppYamlConfig()
            return self._yaml_config

        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)
            self._yaml_config = AppYamlConfig(**data)
            return self._yaml_config
        except Exception:
            # Fallback to defaults
            self._yaml_config = AppYamlConfig()
            return self._yaml_config

    @property
    def yaml(self) -> AppYamlConfig:
        """Property accessor for YAML config."""
        return self.load_yaml_config()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# ──────────────────────────────────────────────────────────────
#  Global settings instance
# ──────────────────────────────────────────────────────────────

settings = Settings()

# Ensure SYNC_DATABASE_URL is set
if not settings.SYNC_DATABASE_URL:
    settings.SYNC_DATABASE_URL = settings.DATABASE_URL.replace("+async", "")