"""Add Service Broker objects (message type, contract, queue, service)

Revision ID: 003
Revises: 002
Create Date: 2025-01-03 00:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mssql import NVARCHAR
from app.utils.constants import SB_QUEUE_JOBS, SB_SERVICE_JOBS, SB_CONTRACT, SB_MESSAGE_TYPE

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration is MS SQL Server specific.
    # It will be skipped on SQLite via dialect branching in env.py.
    # We use `op.execute` with raw SQL.
    # We'll wrap in a dialect check to avoid errors on SQLite.
    # But env.py already handles this by skipping when dialect is sqlite.
    # So we can safely execute these statements; they will only be run on MSSQL.

    # Enable Service Broker on the database (if not already)
    op.execute("ALTER DATABASE CURRENT SET ENABLE_BROKER WITH ROLLBACK IMMEDIATE")

    # Create message type
    op.execute(f"""
        IF NOT EXISTS (SELECT * FROM sys.service_message_types WHERE name = '{SB_MESSAGE_TYPE}')
        CREATE MESSAGE TYPE [{SB_MESSAGE_TYPE}] VALIDATION = WELL_FORMED_XML
    """)

    # Create contract
    op.execute(f"""
        IF NOT EXISTS (SELECT * FROM sys.service_contracts WHERE name = '{SB_CONTRACT}')
        CREATE CONTRACT [{SB_CONTRACT}] ([{SB_MESSAGE_TYPE}] SENT BY INITIATOR)
    """)

    # Create queue
    op.execute(f"""
        IF NOT EXISTS (SELECT * FROM sys.service_queues WHERE name = '{SB_QUEUE_JOBS}')
        CREATE QUEUE dbo.{SB_QUEUE_JOBS} WITH STATUS = ON
    """)

    # Create service
    op.execute(f"""
        IF NOT EXISTS (SELECT * FROM sys.services WHERE name = '{SB_SERVICE_JOBS}')
        CREATE SERVICE [{SB_SERVICE_JOBS}] ON QUEUE dbo.{SB_QUEUE_JOBS} ([{SB_CONTRACT}])
    """)

    # Create a helper table for queued messages (fallback for simplicity)
    # In production, we'd use the actual Service Broker queues.
    # But for portability, we also keep a table-backed queue for testing.
    op.create_table(
        'service_broker_queue',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('queue_name', sa.String(100), nullable=False),
        sa.Column('message_body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mssql_clustered=True,
    )
    op.create_index(op.f('ix_service_broker_queue_queue_name'), 'service_broker_queue', ['queue_name'], unique=False)
    op.create_index(op.f('ix_service_broker_queue_created_at'), 'service_broker_queue', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop table-backed queue first
    op.drop_table('service_broker_queue')

    # Drop Service Broker objects
    op.execute(f"DROP SERVICE [{SB_SERVICE_JOBS}]")
    op.execute(f"DROP QUEUE dbo.{SB_QUEUE_JOBS}")
    op.execute(f"DROP CONTRACT [{SB_CONTRACT}]")
    op.execute(f"DROP MESSAGE TYPE [{SB_MESSAGE_TYPE}]")