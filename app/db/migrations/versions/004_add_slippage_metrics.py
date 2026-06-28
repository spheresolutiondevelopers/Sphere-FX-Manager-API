"""Add slippage metrics and indexes for performance

Revision ID: 004
Revises: 003
Create Date: 2025-01-04 00:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add slippage_bps column to live_orders (already added in 002, but ensure it exists)
    # If not present, add it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('live_orders')]
    if 'slippage_bps' not in columns:
        op.add_column('live_orders', sa.Column('slippage_bps', sa.Numeric(10, 2), nullable=True))

    # Add fill_price column (already present, but ensure it exists)
    if 'filled_price' not in columns:
        op.add_column('live_orders', sa.Column('filled_price', sa.Numeric(20, 8), nullable=True))

    # Add indexes for performance on live_jobs polling
    op.create_index(op.f('ix_live_jobs_status_created_at'), 'live_jobs', ['status', 'created_at'], unique=False)

    # Add index on signals for date-based queries
    op.create_index(op.f('ix_signals_created_at'), 'signals', ['created_at'], unique=False)

    # Add index on backtest_runs for user lookups
    op.create_index(op.f('ix_backtest_runs_user_id'), 'backtest_runs', ['user_id'], unique=False)

    # Add index on notifications for user and read status
    op.create_index(op.f('ix_notifications_user_id_is_read'), 'notifications', ['user_id', 'is_read'], unique=False)

    # Add index on audit_logs for timestamp
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_notifications_user_id_is_read'), table_name='notifications')
    op.drop_index(op.f('ix_backtest_runs_user_id'), table_name='backtest_runs')
    op.drop_index(op.f('ix_signals_created_at'), table_name='signals')
    op.drop_index(op.f('ix_live_jobs_status_created_at'), table_name='live_jobs')

    # Drop columns if they exist (but we added them in 002, so not necessary)
    # We keep them; no downgrade needed for columns.
    pass