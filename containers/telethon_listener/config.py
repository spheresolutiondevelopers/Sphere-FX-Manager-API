"""
Telethon Listener configuration.
Loaded from environment variables with sensible defaults.
"""

import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


class TelethonConfig:
    """Configuration container for the Telethon listener."""

    # Telegram API credentials
    TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID", 0))
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")

    # FastAPI webhook endpoint
    FASTAPI_URL: str = os.getenv(
        "FASTAPI_URL",
        "http://fastapi:8000/api/v1/webhook/telegram"
    )

    # HMAC secret for request signing
    HMAC_SECRET: str = os.getenv("HMAC_SECRET", "")

    # Channel IDs to listen to (comma-separated)
    _channel_ids_str: str = os.getenv("TELEGRAM_CHANNEL_IDS", "")
    CHANNEL_IDS: List[int] = [
        int(cid.strip()) for cid in _channel_ids_str.split(",") if cid.strip()
    ]

    # Session file path (persistent)
    SESSION_FILE: str = os.getenv("SESSION_FILE", "/app/sessions/session.session")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> bool:
        """Validate that critical configuration is present."""
        if not cls.TELEGRAM_API_ID:
            raise ValueError("TELEGRAM_API_ID is required")
        if not cls.TELEGRAM_API_HASH:
            raise ValueError("TELEGRAM_API_HASH is required")
        if not cls.CHANNEL_IDS:
            raise ValueError("TELEGRAM_CHANNEL_IDS must contain at least one channel ID")
        if not cls.FASTAPI_URL:
            raise ValueError("FASTAPI_URL is required")
        return True


# Singleton instance
config = TelethonConfig()