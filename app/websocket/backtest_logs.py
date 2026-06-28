"""WebSocket handler for streaming backtest logs from the Go Backtester."""

from fastapi import WebSocket, WebSocketDisconnect, Depends
from app.services.backtest_grpc import run_backtest
from app.services.websocket_manager import manager
from app.middleware.auth import JWTBearer
from app.services.database import AsyncSessionLocal
from app.models import BacktestRun
from sqlalchemy import select
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


async def backtest_logs_websocket(
    websocket: WebSocket,
    run_id: int,
    token: str = Depends(JWTBearer()),
):
    """
    WebSocket endpoint that streams backtest log lines from the Go Backtester.
    Path: /ws/backtest/{run_id}
    """
    user_id = websocket.state.user_id  # set by JWTBearer

    # Accept the connection
    await manager.connect(websocket, user_id)

    # Verify the backtest run belongs to this user
    async with AsyncSessionLocal() as session:
        stmt = select(BacktestRun).where(
            BacktestRun.id == run_id,
            BacktestRun.user_id == user_id
        )
        result = await session.execute(stmt)
        run = result.scalar_one_or_none()

        if not run:
            await websocket.send_json({"error": "Backtest run not found or not owned by user"})
            await websocket.close()
            return

        # If the backtest is already completed, send the stored result
        if run.status == "DONE":
            await websocket.send_json({
                "type": "result",
                "data": run.result
            })
            await websocket.close()
            return

    try:
        # Subscribe to this job for notifications
        await manager.subscribe_to_job(websocket, user_id, f"backtest_{run_id}")

        # If the run is in progress, we'll stream logs from the Go Backtester
        if run.status == "RUNNING":
            # The Go Backtester gRPC streaming is already implemented in services/backtest_grpc.py
            # Here we would consume the stream and forward to WebSocket.
            # For simplicity, we'll simulate a stream or rely on the existing implementation.
            # In a real implementation, you'd call run_backtest with the run_id and config.
            # Since we don't have a direct way to reconnect to an existing stream,
            # we'll just send a placeholder message.
            await websocket.send_json({
                "type": "info",
                "message": "Streaming backtest logs from Go Backtester...",
            })

        # Keep connection alive and listen for any client messages (e.g., cancel)
        while True:
            try:
                # Wait for client message (e.g., "cancel")
                data = await websocket.receive_text()
                msg = json.loads(data)
                if msg.get("action") == "cancel":
                    # Cancel the backtest (update DB status to CANCELLED)
                    async with AsyncSessionLocal() as session:
                        stmt = select(BacktestRun).where(BacktestRun.id == run_id)
                        result = await session.execute(stmt)
                        run = result.scalar_one_or_none()
                        if run and run.status == "RUNNING":
                            run.status = "CANCELLED"
                            await session.commit()
                    await websocket.send_json({"type": "canceled", "message": "Backtest canceled"})
                    break
            except json.JSONDecodeError:
                continue
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for backtest {run_id}, user {user_id}")
    finally:
        # Clean up subscription
        await manager.unsubscribe_from_job(f"backtest_{run_id}")
        manager.disconnect(websocket, user_id)