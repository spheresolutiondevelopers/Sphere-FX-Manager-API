"""Webhook endpoints for external signal sources (Telegram, etc.)."""

from fastapi import APIRouter, Request, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.models import Signal
from app.services.extraction_grpc import extract_signal
from app.services.websocket_manager import manager
from app.config import settings
from app.exceptions import ValidationError
import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/telegram", status_code=status.HTTP_202_ACCEPTED)
async def telegram_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """
    Incoming webhook from Telethon listener.
    Expects a JSON body with 'raw_text' and an HMAC signature in headers.
    """
    # Verify HMAC signature (if configured)
    if settings.HMAC_SECRET:
        signature = request.headers.get("X-HMAC-Signature")
        if not signature:
            raise ValidationError("Missing HMAC signature")
        body = await request.body()
        expected = hmac.new(
            settings.HMAC_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValidationError("Invalid HMAC signature")

    # Parse body
    try:
        data = await request.json()
    except Exception:
        raise ValidationError("Invalid JSON body")

    raw_text = data.get("raw_text")
    if not raw_text:
        raise ValidationError("Missing raw_text field")

    # Attempt extraction
    try:
        extract_response = await extract_signal(raw_text)
        if extract_response:
            parsed = extract_response.parsed_signal
            # Create signal record
            signal = Signal(
                raw_text=raw_text,
                symbol=parsed.symbol,
                action=parsed.action,
                order_type=parsed.order_type or "MARKET",
                entry_price=parsed.entry_price,
                stop_loss=parsed.stop_loss,
                take_profit=parsed.take_profit,
                confidence=parsed.confidence or 0,
                created_by=1,  # System user (or from channel mapping)
                status="PENDING",
            )
            session.add(signal)
            await session.commit()
            await session.refresh(signal)

            # Broadcast to WebSocket subscribers
            await manager.broadcast({
                "type": "signal_feed",
                "signal_id": signal.id,
                "symbol": signal.symbol,
                "action": signal.action,
                "entry_price": float(signal.entry_price) if signal.entry_price else None,
            })

            logger.info(f"Webhook: signal {signal.id} created from Telegram")
        else:
            logger.warning(f"Webhook: extraction failed for raw_text: {raw_text[:50]}...")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise ValidationError(f"Extraction failed: {str(e)}")

    return {"status": "accepted", "signal_id": signal.id if extract_response else None}