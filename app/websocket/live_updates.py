"""WebSocket handler for real-time live job updates via Service Broker."""

from fastapi import WebSocket, WebSocketDisconnect, Depends
from app.middleware.auth import JWTBearer
from app.services.websocket_manager import manager
from app.services.broker_service import receive_notification
from app.services.database import AsyncSessionLocal
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


async def live_updates_websocket(
    websocket: WebSocket,
    account_id: int,
    token: str = Depends(JWTBearer()),
):
    """
    WebSocket endpoint for live job updates for a specific account.
    Path: /ws/live/{account_id}
    """
    user_id = websocket.state.user_id

    # Accept the connection
    await manager.connect(websocket, user_id)

    # Verify the account belongs to this user
    from app.models import MT5Account
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        stmt = select(MT5Account).where(
            MT5Account.id == account_id,
            MT5Account.user_id == user_id
        )
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()
        if not account:
            await websocket.send_json({"error": "Account not found or not owned"})
            await websocket.close()
            return

    # Subscribe to the user for general notifications
    await manager.subscribe_to_job(websocket, user_id, f"account_{account_id}")

    try:
        # Keep connection alive and poll Service Broker for new messages
        # We'll poll the broker every 500ms for efficiency.
        # In production, consider using a dedicated background task that pushes to all WS.
        # This simple approach works for moderate load.
        while True:
            # Check for any messages from Service Broker for this user/account
            async with AsyncSessionLocal() as session:
                # Check both account-specific and general job queues
                # Here we assume we have a queue per account or we use a generic queue with filters
                # For simplicity, we'll check the main queue and filter by account_id in the message.
                msg = await receive_notification(session, "live_jobs_queue")
                if msg:
                    # If the message matches this account_id, forward to WS
                    if msg.get("account_id") == account_id:
                        await websocket.send_json(msg)

            # Also allow the client to send messages (e.g., ping)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                # Handle any client commands
                try:
                    cmd = json.loads(data)
                    if cmd.get("action") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info(f"Live WebSocket disconnected for account {account_id}, user {user_id}")
    finally:
        manager.disconnect(websocket, user_id)