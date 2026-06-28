"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mssql import NVARCHAR, UNIQUEIDENTIFIER
import uuid

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('role', sa.String(length=20), server_default='user', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create telegram_channels table
    op.create_table(
        'telegram_channels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_channel_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('added_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_channel_id')
    )
    op.create_index(op.f('ix_telegram_channels_id'), 'telegram_channels', ['id'], unique=False)
    op.create_index(op.f('ix_telegram_channels_telegram_channel_id'), 'telegram_channels', ['telegram_channel_id'], unique=True)

    # Create symbols table
    op.create_table(
        'symbols',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=20), nullable=False),
        sa.Column('broker_name', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('pip_value', sa.Numeric(10, 6), nullable=False),
        sa.Column('min_lot', sa.Numeric(10, 2), nullable=False),
        sa.Column('max_lot', sa.Numeric(10, 2), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_symbols_id'), 'symbols', ['id'], unique=False)
    op.create_index(op.f('ix_symbols_name'), 'symbols', ['name'], unique=False)

    # Create mt5_accounts table
    op.create_table(
        'mt5_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('login', sa.String(length=50), nullable=False),
        sa.Column('password', sa.String(length=255), nullable=False),
        sa.Column('server', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('balance_cache', sa.Numeric(12, 2), nullable=True),
        sa.Column('equity_cache', sa.Numeric(12, 2), nullable=True),
        sa.Column('last_sync', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mt5_accounts_id'), 'mt5_accounts', ['id'], unique=False)

    # Create licenses table
    op.create_table(
        'licenses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('license_key_hash', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('features', sa.JSON(), nullable=False),
        sa.Column('issued_at', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('license_key_hash')
    )

    # Create signals table
    op.create_table(
        'signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('action', sa.String(length=4), nullable=False),
        sa.Column('order_type', sa.String(length=12), nullable=False),
        sa.Column('entry_price', sa.Numeric(20, 8), nullable=True),
        sa.Column('stop_loss', sa.Numeric(20, 8), nullable=True),
        sa.Column('take_profit', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['telegram_channels.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_signals_id'), 'signals', ['id'], unique=False)
    op.create_index(op.f('ix_signals_symbol'), 'signals', ['symbol'], unique=False)

    # Create backtest_runs table
    op.create_table(
        'backtest_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtest_runs_id'), 'backtest_runs', ['id'], unique=False)

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('message', sa.String(length=500), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('diff', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('GETUTCDATE()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('notifications')
    op.drop_table('backtest_runs')
    op.drop_table('signals')
    op.drop_table('licenses')
    op.drop_table('mt5_accounts')
    op.drop_table('symbols')
    op.drop_table('telegram_channels')
    op.drop_table('users')