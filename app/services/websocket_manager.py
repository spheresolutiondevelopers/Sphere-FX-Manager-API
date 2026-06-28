"""WebSocket connection manager for real-time updates."""

from typing import Dict, Set, Optional
from fastapi import WebSocket
import asyncio
import json


class ConnectionManager:
    """Manages active WebSocket connections per user and job."""

    def __init__(self):
        # user_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # job_id -> user_id mapping
        self.job_subscriptions: Dict[str, int] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def subscribe_to_job(self, websocket: WebSocket, user_id: int, job_id: str) -> None:
        """Associate a job ID with a user for push notifications."""
        self.job_subscriptions[job_id] = user_id

    async def unsubscribe_from_job(self, job_id: str) -> None:
        """Remove a job subscription."""
        self.job_subscriptions.pop(job_id, None)

    async def send_to_user(self, user_id: int, message: dict) -> None:
        """Send a JSON message to all WebSockets for a given user."""
        if user_id not in self.active_connections:
            return
        data = json.dumps(message)
        for ws in self.active_connections[user_id]:
            try:
                await ws.send_text(data)
            except Exception:
                # Connection may be dead; will be cleaned up later
                pass

    async def send_to_job_subscribers(self, job_id: str, message: dict) -> None:
        """Send a message to the user subscribed to a specific job."""
        user_id = self.job_subscriptions.get(job_id)
        if user_id is not None:
            await self.send_to_user(user_id, message)

    async def broadcast(self, message: dict) -> None:
        """Broadcast to all connected users."""
        data = json.dumps(message)
        for user_id, connections in self.active_connections.items():
            for ws in connections:
                try:
                    await ws.send_text(data)
                except Exception:
                    pass


# Singleton instance
manager = ConnectionManager()