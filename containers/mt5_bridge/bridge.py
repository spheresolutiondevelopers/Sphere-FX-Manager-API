#!/usr/bin/env python
"""
MT5 Bridge HTTP server.
Receives order requests from Go Live Worker and executes them via MetaTrader5.
"""

import logging
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from config import config
from mt5_client import MT5Client, MT5OrderRequest, MT5OrderResult

# ─── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="MT5 Bridge", version="1.0.0")

# ─── MT5 Client Singleton ──────────────────────────────────
mt5_client = MT5Client(
    account=config.MT5_ACCOUNT,
    password=config.MT5_PASSWORD,
    server=config.MT5_SERVER,
    terminal_path=config.MT5_TERMINAL_PATH,
)


# ─── Schemas ──────────────────────────────────────────────
class OrderRequest(BaseModel):
    symbol: str = Field(..., max_length=20)
    action: str = Field(..., pattern="^(BUY|SELL)$")
    order_type: str = Field(..., pattern="^(MARKET|LIMIT|STOP|STOP_LIMIT)$")
    lot_size: float = Field(..., gt=0, le=100)
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[List[Dict[str, Any]]] = None  # list of {level: int, price: float}
    slippage_bps: Optional[float] = None


class OrderResponse(BaseModel):
    ticket: int
    fill_price: float
    slippage_bps: float
    status: str


# ─── Endpoints ────────────────────────────────────────────
@app.post("/execute", response_model=OrderResponse)
async def execute_order(order: OrderRequest):
    """Execute a trade order via MT5."""
    try:
        # Convert to MT5OrderRequest
        mt5_order = MT5OrderRequest(
            symbol=order.symbol,
            action=order.action,
            order_type=order.order_type,
            lot_size=order.lot_size,
            entry_price=order.entry_price,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
        )

        result: MT5OrderResult = mt5_client.send_order(mt5_order)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order failed: {result.error_message}"
            )

        return OrderResponse(
            ticket=result.ticket,
            fill_price=result.fill_price,
            slippage_bps=result.slippage_bps,
            status="FILLED",
        )

    except Exception as e:
        logger.error(f"Order execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Check if MT5 terminal is connected."""
    if mt5_client.is_connected():
        return {"status": "connected", "account": config.MT5_ACCOUNT}
    else:
        return {"status": "disconnected"}


# ─── Entry ──────────────────────────────────────────────────
if __name__ == "__main__":
    # Validate config
    config.validate()
    logger.info("Starting MT5 Bridge...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)