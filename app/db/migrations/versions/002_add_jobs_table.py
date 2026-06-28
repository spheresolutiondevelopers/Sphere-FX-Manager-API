"""Add live_jobs table

Revision ID: 002
Revises: 001
Create Date: 2025-01-02 00:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create live_jobs table (the queue)
    op.create_table(
        'live_jobs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('signal_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lot_size', sa.Numeric(10, 4), nullable=False),
        sa.Column('status', sa.String(20), server_default='PENDING', nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('claimed_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['mt5_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('signal_id', 'account_id', name='uq_job_signal_account')
    )
    op.create_index(op.f('ix_live_jobs_id'), 'live_jobs', ['id'], unique=False)

    # Create live_orders table
    op.create_table(
        'live_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(36), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('broker_order_id', sa.String(50), nullable=True),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('action', sa.String(4), nullable=False),
        sa.Column('order_type', sa.String(20), nullable=False),
        sa.Column('requested_price', sa.Numeric(20, 8), nullable=False),
        sa.Column('filled_price', sa.Numeric(20, 8), nullable=True),
        sa.Column('lot_size', sa.Numeric(10, 4), nullable=False),
        sa.Column('slippage_bps', sa.Numeric(10, 2), nullable=True),
        sa.Column('status', sa.String(20), server_default='PENDING', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.Column('filled_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['live_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['mt5_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_live_orders_id'), 'live_orders', ['id'], unique=False)

    # Create live_positions table
    op.create_table(
        'live_positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(36), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('broker_position_id', sa.String(50), nullable=True),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('action', sa.String(4), nullable=False),
        sa.Column('entry_price', sa.Numeric(20, 8), nullable=False),
        sa.Column('current_price', sa.Numeric(20, 8), nullable=True),
        sa.Column('lot_size', sa.Numeric(10, 4), nullable=False),
        sa.Column('stop_loss', sa.Numeric(20, 8), nullable=True),
        sa.Column('take_profit', sa.JSON(), nullable=True),
        sa.Column('remaining_lots', sa.Numeric(10, 4), nullable=True),
        sa.Column('status', sa.String(20), server_default='OPEN', nullable=False),
        sa.Column('pnl', sa.Numeric(12, 2), nullable=True),
        sa.Column('opened_at', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('close_reason', sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['live_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['live_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['mt5_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_live_positions_id'), 'live_positions', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('live_positions')
    op.drop_table('live_orders')
    op.drop_table('live_jobs')