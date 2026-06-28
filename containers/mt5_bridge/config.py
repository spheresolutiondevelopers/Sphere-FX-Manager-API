"""
MT5 Bridge configuration.
Loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class MT5BridgeConfig:
    """Configuration container for the MT5 Bridge."""

    # MetaTrader 5 credentials
    MT5_ACCOUNT: int = int(os.getenv("MT5_ACCOUNT", 0))
    MT5_PASSWORD: str = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER: str = os.getenv("MT5_SERVER", "")
    MT5_TERMINAL_PATH: str = os.getenv("MT5_TERMINAL_PATH", "")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> bool:
        """Validate that critical configuration is present."""
        if not cls.MT5_ACCOUNT:
            raise ValueError("MT5_ACCOUNT is required")
        if not cls.MT5_PASSWORD:
            raise ValueError("MT5_PASSWORD is required")
        if not cls.MT5_SERVER:
            raise ValueError("MT5_SERVER is required")
        if not cls.MT5_TERMINAL_PATH:
            raise ValueError("MT5_TERMINAL_PATH is required (must point to terminal64.exe)")
        return True


# Singleton instance
config = MT5BridgeConfig()