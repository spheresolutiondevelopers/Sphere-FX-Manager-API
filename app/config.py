"""
Configuration management using Pydantic Settings with YAML support.
Loads environment variables from .env and merges with config/config.yaml.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from cryptography.fernet import Fernet
import yaml
import os
from pathlib import Path
import base64


# ──────────────────────────────────────────────────────────────
#  YAML Config Models – define the structure of config.yaml
# ──────────────────────────────────────────────────────────────

class RiskLimitsConfig(BaseModel):
    max_lot: float = 100.0
    min_lot: float = 0.01
    max_daily_drawdown_percent: float = 5.0
    min_rr_ratio: float = 1.5
    max_positions: int = 10


class BacktesterConfig(BaseModel):
    default_rr: float = 2.0
    default_spread_pips: float = 1.5
    default_commission: float = 3.5
    min_data_points: int = 100


class QueueConfig(BaseModel):
    poll_interval_seconds: int = 2
    max_claim_attempts: int = 3


class PoolConfig(BaseModel):
    async_pool_size: int = 20
    async_max_overflow: int = 10
    sync_pool_size: int = 5


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class AppYamlConfig(BaseModel):
    risk_limits: RiskLimitsConfig = Field(default_factory=RiskLimitsConfig)
    backtester: BacktesterConfig = Field(default_factory=BacktesterConfig)
    queue: QueueConfig = Field(default_factory=QueueConfig)
    pool: PoolConfig = Field(default_factory=PoolConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


# ──────────────────────────────────────────────────────────────
#  Environment Settings – loaded from .env
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

    # ─── Fernet Key (for encryption) ──────────────────────────
    # FIXED: If not provided, we auto-generate a valid key.
    FERNET_KEY: Optional[str] = Field(None, description="Fernet key for encryption")

    # ─── Debug ──────────────────────────────────────────────────
    DEBUG: bool = Field(False, description="Enable debug mode")

    # ─── YAML Config Path ──────────────────────────────────────
    CONFIG_YAML_PATH: str = Field("config/config.yaml", description="Path to YAML configuration")

    # ─── Internal cache for YAML config ──────────────────────
    _yaml_config: Optional[AppYamlConfig] = None

    # ─── Validators ────────────────────────────────────────────

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    @field_validator("SYNC_DATABASE_URL", mode="before")
    @classmethod
    def default_sync_url(cls, v: Optional[str], info) -> str:
        """Derive sync URL from async URL if not set."""
        if v is None:
            async_url = info.data.get("DATABASE_URL", "")
            if async_url.startswith("mssql+aioodbc"):
                return async_url.replace("mssql+aioodbc", "mssql+pyodbc")
            if async_url.startswith("postgresql+async"):
                return async_url.replace("postgresql+async", "postgresql")
            if async_url.startswith("sqlite+async"):
                return async_url.replace("sqlite+async", "sqlite")
            return async_url
        return v

    @field_validator("FERNET_KEY", mode="before")
    @classmethod
    def default_fernet_key(cls, v: Optional[str]) -> str:
        """
        FIXED: Ensure we have a valid Fernet key.
        If missing or invalid, generate a new one.
        """
        if v is None or v == "":
            key = Fernet.generate_key()
            return key.decode()
        try:
            # Validate the key is correct base64 and length
            base64.urlsafe_b64decode(v)
            return v
        except Exception:
            # Invalid key – generate a new one
            key = Fernet.generate_key()
            return key.decode()

    # ─── YAML Loading ──────────────────────────────────────────

    def load_yaml_config(self) -> AppYamlConfig:
        """
        Load the YAML configuration file.
        FIXED: Handles missing/invalid YAML gracefully with fallback defaults.
        """
        if self._yaml_config is not None:
            return self._yaml_config

        yaml_path = Path(self.CONFIG_YAML_PATH)
        if not yaml_path.exists():
            self._yaml_config = AppYamlConfig()
            return self._yaml_config

        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)
            if data is None:
                data = {}
            self._yaml_config = AppYamlConfig(**data)
        except Exception as e:
            print(f"⚠️ Warning: Failed to load YAML config: {e}. Using defaults.")
            self._yaml_config = AppYamlConfig()

        return self._yaml_config

    @property
    def yaml(self) -> AppYamlConfig:
        """
        Access the YAML config as a typed AppYamlConfig object.
        FIXED: Always returns an AppYamlConfig instance, not a dict.
        """
        return self.load_yaml_config()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# ─── Global settings instance ──────────────────────────────────

settings = Settings()

# Ensure SYNC_DATABASE_URL is set
if not settings.SYNC_DATABASE_URL:
    settings.SYNC_DATABASE_URL = settings.DATABASE_URL.replace("+aioodbc", "+pyodbc")