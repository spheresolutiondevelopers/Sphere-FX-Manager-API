from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
import yaml
import os
from pathlib import Path
import re


class AppYamlConfig(BaseModel):
    risk_limits: Dict[str, Any] = Field(default_factory=dict)
    backtester: Dict[str, Any] = Field(default_factory=dict)
    queue: Dict[str, Any] = Field(default_factory=dict)
    pool: Dict[str, Any] = Field(default_factory=dict)
    logging: Dict[str, Any] = Field(default_factory=dict)


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

    # ─── Fernet Key ────────────────────────────────────────────
    FERNET_KEY: Optional[str] = Field(None, description="Fernet key for encryption")

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
        if v is None:
            # Generate a random key for development
            from cryptography.fernet import Fernet
            return Fernet.generate_key().decode()
        return v

    def load_yaml_config(self) -> AppYamlConfig:
        """Load and parse the YAML configuration file."""
        if self._yaml_config is not None:
            return self._yaml_config

        yaml_path = Path(self.CONFIG_YAML_PATH)
        if not yaml_path.exists():
            self._yaml_config = AppYamlConfig()
            return self._yaml_config

        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)
            self._yaml_config = AppYamlConfig(**data)
            return self._yaml_config
        except Exception:
            self._yaml_config = AppYamlConfig()
            return self._yaml_config

    @property
    def yaml(self) -> AppYamlConfig:
        return self.load_yaml_config()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()

if not settings.SYNC_DATABASE_URL:
    settings.SYNC_DATABASE_URL = settings.DATABASE_URL.replace("+aioodbc", "+pyodbc")