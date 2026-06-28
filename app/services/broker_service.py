"""MS SQL Service Broker wrapper for async pub/sub."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
from typing import Dict, Any, Optional


async def send_notification(
    session: AsyncSession,
    queue_name: str,  # e.g., 'live_jobs_queue'
    message: Dict[str, Any],
) -> bool:
    """
    Send a message via Service Broker.
    Assumes the queue and service are already created.
    """
    # Convert message to JSON string
    msg_body = json.dumps(message)

    # Use a simple stored procedure or direct DML
    # SQL Server Service Broker send via SEND ON CONVERSATION
    # We'll use a simpler approach: insert into a broker queue table.
    # For production, you would use SEND ON CONVERSATION with proper contracts.
    # Here we simulate by inserting into a dedicated queue table.

    raw_sql = text("""
        INSERT INTO dbo.service_broker_queue (queue_name, message_body, created_at)
        VALUES (:queue_name, :message_body, GETUTCDATE())
    """)
    await session.execute(raw_sql, {
        "queue_name": queue_name,
        "message_body": msg_body,
    })
    await session.flush()
    return True


async def receive_notification(
    session: AsyncSession,
    queue_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Receive and delete the next message from the queue.
    """
    raw_sql = text("""
        DELETE TOP (1)
        FROM dbo.service_broker_queue
        OUTPUT deleted.message_body
        WHERE queue_name = :queue_name
        ORDER BY created_at ASC
    """)
    result = await session.execute(raw_sql, {"queue_name": queue_name})
    row = result.fetchone()
    if row:
        return json.loads(row[0])
    return None


async def create_broker_objects(session: AsyncSession) -> None:
    """
    Create Service Broker objects (queue, service, contract, message type)
    if they do not exist. This is idempotent and should be called during migration.
    """
    # Message type
    await session.execute(text("""
        IF NOT EXISTS (SELECT * FROM sys.service_message_types WHERE name = '//sphere/default')
        CREATE MESSAGE TYPE [//sphere/default] VALIDATION = WELL_FORMED_XML
    """))
    # Contract
    await session.execute(text("""
        IF NOT EXISTS (SELECT * FROM sys.service_contracts WHERE name = '//sphere/contract')
        CREATE CONTRACT [//sphere/contract] ([//sphere/default] SENT BY INITIATOR)
    """))
    # Queue
    await session.execute(text("""
        IF NOT EXISTS (SELECT * FROM sys.service_queues WHERE name = 'live_jobs_queue')
        CREATE QUEUE dbo.live_jobs_queue WITH STATUS = ON
    """))
    # Service
    await session.execute(text("""
        IF NOT EXISTS (SELECT * FROM sys.services WHERE name = 'live_jobs_service')
        CREATE SERVICE [live_jobs_service] ON QUEUE dbo.live_jobs_queue ([//sphere/contract])
    """))
    await session.flush()