"""Application-wide constants."""

from decimal import Decimal

# ─── Signal Actions ─────────────────────────────────────────────
ACTIONS = {"BUY", "SELL"}
ACTION_BUY = "BUY"
ACTION_SELL = "SELL"

# ─── Order Types ────────────────────────────────────────────────
ORDER_TYPES = {"MARKET", "LIMIT", "STOP", "STOP_LIMIT"}
ORDER_MARKET = "MARKET"
ORDER_LIMIT = "LIMIT"
ORDER_STOP = "STOP"
ORDER_STOP_LIMIT = "STOP_LIMIT"

# ─── Signal Statuses ───────────────────────────────────────────
SIGNAL_STATUSES = {"PENDING", "EXECUTED", "EXPIRED", "CANCELLED"}
STATUS_PENDING = "PENDING"
STATUS_EXECUTED = "EXECUTED"
STATUS_EXPIRED = "EXPIRED"
STATUS_CANCELLED = "CANCELLED"

# ─── Job Statuses ──────────────────────────────────────────────
JOB_STATUSES = {"PENDING", "CLAIMED", "SUCCESS", "FAILED", "CANCELLED"}
JOB_PENDING = "PENDING"
JOB_CLAIMED = "CLAIMED"
JOB_SUCCESS = "SUCCESS"
JOB_FAILED = "FAILED"
JOB_CANCELLED = "CANCELLED"

# ─── Order Statuses ────────────────────────────────────────────
ORDER_STATUSES = {"PENDING", "FILLED", "CANCELLED", "REJECTED"}
ORDER_PENDING = "PENDING"
ORDER_FILLED = "FILLED"
ORDER_CANCELLED = "CANCELLED"
ORDER_REJECTED = "REJECTED"

# ─── Position Statuses ─────────────────────────────────────────
POSITION_STATUSES = {"OPEN", "CLOSED", "PARTIAL"}
POSITION_OPEN = "OPEN"
POSITION_CLOSED = "CLOSED"
POSITION_PARTIAL = "PARTIAL"

# ─── Backtest Statuses ─────────────────────────────────────────
BACKTEST_STATUSES = {"PENDING", "RUNNING", "DONE", "FAILED", "CANCELLED"}
BACKTEST_PENDING = "PENDING"
BACKTEST_RUNNING = "RUNNING"
BACKTEST_DONE = "DONE"
BACKTEST_FAILED = "FAILED"
BACKTEST_CANCELLED = "CANCELLED"

# ─── Notification Types ────────────────────────────────────────
NOTIFICATION_TYPES = {"INFO", "WARNING", "ERROR", "SUCCESS"}
NOTIFICATION_INFO = "INFO"
NOTIFICATION_WARNING = "WARNING"
NOTIFICATION_ERROR = "ERROR"
NOTIFICATION_SUCCESS = "SUCCESS"

# ─── Symbol Categories ─────────────────────────────────────────
SYMBOL_CATEGORIES = {"forex", "metal", "crypto", "index"}
CAT_FOREX = "forex"
CAT_METAL = "metal"
CAT_CRYPTO = "crypto"
CAT_INDEX = "index"

# ─── WebSocket Message Types ──────────────────────────────────
WS_MESSAGE_TYPES = {
    "JOB_UPDATE": "job_update",
    "POSITION_UPDATE": "position_update",
    "SIGNAL_FEED": "signal_feed",
    "BACKTEST_LOG": "backtest_log",
    "BACKTEST_RESULT": "backtest_result",
    "ERROR": "error",
    "PONG": "pong",
}

# ─── Default Values ────────────────────────────────────────────
DEFAULT_RR_RATIO = Decimal("2.0")
DEFAULT_SPREAD_PIPS = Decimal("1.5")
DEFAULT_MIN_LOT = Decimal("0.01")
DEFAULT_MAX_LOT = Decimal("100.0")
DEFAULT_COMMISSION_PCT = Decimal("0.05")
DEFAULT_MAX_DAILY_DRAWDOWN_PCT = Decimal("5.0")
DEFAULT_MAX_POSITIONS = 10

# ─── Service Broker Queue Names ───────────────────────────────
SB_QUEUE_JOBS = "live_jobs_queue"
SB_SERVICE_JOBS = "live_jobs_service"
SB_CONTRACT = "//sphere/contract"
SB_MESSAGE_TYPE = "//sphere/default"

# ─── License Feature Flags ─────────────────────────────────────
LICENSE_FEATURES = {
    "max_accounts": "max_accounts",
    "max_channels": "max_channels",
    "backtesting": "backtesting",
    "live_trading": "live_trading",
    "ai_advisor": "ai_advisor",
}