"""
MetaTrader5 client wrapper.
"""

import logging
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)


@dataclass
class MT5OrderRequest:
    symbol: str
    action: str  # BUY, SELL
    order_type: str  # MARKET, LIMIT, STOP, STOP_LIMIT
    lot_size: float
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[List[Dict[str, Any]]] = None


@dataclass
class MT5OrderResult:
    success: bool
    ticket: int
    fill_price: float
    slippage_bps: float
    error_message: Optional[str] = None


class MT5Client:
    def __init__(self, account: int, password: str, server: str, terminal_path: str = None):
        self.account = account
        self.password = password
        self.server = server
        self.terminal_path = terminal_path
        self._connected = False

    def connect(self) -> bool:
        """Initialize and connect to MT5 terminal."""
        if self._connected:
            return True

        if self.terminal_path:
            if not mt5.initialize(self.terminal_path):
                logger.error(f"MT5 initialize failed: {mt5.last_error()}")
                return False
        else:
            if not mt5.initialize():
                logger.error(f"MT5 initialize failed: {mt5.last_error()}")
                return False

        # Login
        if not mt5.login(self.account, password=self.password, server=self.server):
            logger.error(f"MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False

        self._connected = True
        logger.info(f"MT5 connected: account {self.account}")
        return True

    def is_connected(self) -> bool:
        return self._connected and mt5.terminal_info() is not None

    def send_order(self, request: MT5OrderRequest) -> MT5OrderResult:
        """Send a market or pending order."""
        if not self.connect():
            return MT5OrderResult(False, 0, 0.0, 0.0, "MT5 not connected")

        # Prepare order request
        symbol_info = mt5.symbol_info(request.symbol)
        if not symbol_info:
            return MT5OrderResult(False, 0, 0.0, 0.0, f"Symbol {request.symbol} not found")

        # Determine order type and action
        order_type = mt5.ORDER_TYPE_BUY if request.action == "BUY" else mt5.ORDER_TYPE_SELL
        if request.order_type == "LIMIT":
            order_type = mt5.ORDER_TYPE_BUY_LIMIT if request.action == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT
        elif request.order_type == "STOP":
            order_type = mt5.ORDER_TYPE_BUY_STOP if request.action == "BUY" else mt5.ORDER_TYPE_SELL_STOP
        elif request.order_type == "STOP_LIMIT":
            order_type = mt5.ORDER_TYPE_BUY_STOP_LIMIT if request.action == "BUY" else mt5.ORDER_TYPE_SELL_STOP_LIMIT

        # Build order request
        mt5_request = {
            "action": mt5.TRADE_ACTION_DEAL if request.order_type == "MARKET" else mt5.TRADE_ACTION_PENDING,
            "symbol": request.symbol,
            "volume": request.lot_size,
            "type": order_type,
            "price": request.entry_price or symbol_info.ask if request.action == "BUY" else request.entry_price or symbol_info.bid,
            "sl": request.stop_loss,
            "tp": request.take_profit[0]["price"] if request.take_profit else None,  # simple: first TP
            "deviation": 20,
            "magic": 123456,
            "comment": "Sphere FX Manager",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send order
        result = mt5.order_send(mt5_request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Order failed: {result.retcode} - {result.comment}"
            logger.error(error_msg)
            return MT5OrderResult(False, 0, 0.0, 0.0, error_msg)

        # Calculate slippage
        slippage_bps = 0.0
        if request.entry_price and result.price:
            slippage_bps = abs(result.price - request.entry_price) / request.entry_price * 10000

        return MT5OrderResult(
            success=True,
            ticket=result.order,
            fill_price=result.price,
            slippage_bps=slippage_bps,
        )

    def shutdown(self):
        if self._connected:
            mt5.shutdown()
            self._connected = False