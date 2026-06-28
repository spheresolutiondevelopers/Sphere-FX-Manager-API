#!/usr/bin/env python3
"""
Telethon listener service.
Subscribes to configured Telegram channels and forwards messages to FastAPI.
"""

import asyncio
import logging
import hmac
import hashlib
import json
from datetime import datetime

import httpx
from telethon import TelegramClient, events
from telethon.tl.types import Message

from config import config

# ─── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ─── Telegram Client ──────────────────────────────────────
client = TelegramClient(
    config.SESSION_FILE,
    config.TELEGRAM_API_ID,
    config.TELEGRAM_API_HASH
)


# ─── Webhook Forwarder ────────────────────────────────────
async def forward_to_api(raw_text: str, chat_id: int, message_id: int) -> bool:
    """Forward a raw message to the FastAPI webhook with HMAC signature."""
    payload = {
        "raw_text": raw_text,
        "chat_id": chat_id,
        "message_id": message_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    body = json.dumps(payload).encode()

    headers = {"Content-Type": "application/json"}
    if config.HMAC_SECRET:
        sig = hmac.new(
            config.HMAC_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        headers["X-HMAC-Signature"] = sig

    async with httpx.AsyncClient(timeout=10.0) as http:
        try:
            resp = await http.post(config.FASTAPI_URL, content=body, headers=headers)
            if resp.status_code in (200, 202):
                logger.info(f"Forwarded message {message_id} from chat {chat_id}")
                return True
            else:
                logger.error(f"API returned {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Forward failed: {e}")
            return False


# ─── Event Handlers ───────────────────────────────────────
@client.on(events.NewMessage(chats=config.CHANNEL_IDS))
async def handle_new_message(event: events.NewMessage.Event):
    """Handle a new Telegram message."""
    msg: Message = event.message
    if not msg or not msg.message:
        return

    # Skip forwarded messages (optional)
    if msg.forward:
        logger.debug(f"Skipping forwarded message {msg.id}")
        return

    raw_text = msg.message
    chat_id = msg.chat_id
    message_id = msg.id

    logger.info(f"Received message {message_id} from chat {chat_id}: {raw_text[:50]}...")
    await forward_to_api(raw_text, chat_id, message_id)


# ─── Main Entry ────────────────────────────────────────────
async def main():
    """Start the Telethon listener."""
    # Validate configuration
    config.validate()

    logger.info("Starting Telethon listener...")
    await client.start()
    logger.info(f"Client started, listening to channels: {config.CHANNEL_IDS}")

    # Log connected chats
    for chat_id in config.CHANNEL_IDS:
        try:
            entity = await client.get_entity(int(chat_id))
            logger.info(f"Listening to: {entity.title} ({entity.id})")
        except Exception as e:
            logger.error(f"Could not get entity for {chat_id}: {e}")

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")