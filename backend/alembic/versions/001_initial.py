"""Initial migration.

Revision ID: 001_initial
Revises: None
Create Date: 2026-07-15 16:43:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create daily_summary table
    op.create_table(
        'daily_summary',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('capital_base', sa.Float(), nullable=False),
        sa.Column('realized_pnl', sa.Float(), nullable=False),
        sa.Column('unrealized_pnl', sa.Float(), nullable=False),
        sa.Column('max_intraday_drawdown', sa.Float(), nullable=False),
        sa.Column('breaker_triggers_count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_daily_summary_date'), 'daily_summary', ['date'], unique=True)
    op.create_index(op.f('ix_daily_summary_id'), 'daily_summary', ['id'], unique=False)

    # Create positions_snapshot table
    op.create_table(
        'positions_snapshot',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('qty', sa.Integer(), nullable=False),
        sa.Column('ltp', sa.Float(), nullable=False),
        sa.Column('exposure', sa.Float(), nullable=False),
        sa.Column('unrealized_pnl', sa.Float(), nullable=False),
        sa.Column('margin_used', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_positions_snapshot_id'), 'positions_snapshot', ['id'], unique=False)
    op.create_index(op.f('ix_positions_snapshot_ts'), 'positions_snapshot', ['ts'], unique=False)

    # Create risk_config table
    op.create_table(
        'risk_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_config_id'), 'risk_config', ['id'], unique=False)
    op.create_index(op.f('ix_risk_config_key'), 'risk_config', ['key'], unique=True)

    # Create risk_events table
    op.create_table(
        'risk_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('breaker_type', sa.String(length=50), nullable=False),
        sa.Column('details_json', sa.Text(), nullable=False),
        sa.Column('action_taken', sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_events_id'), 'risk_events', ['id'], unique=False)
    op.create_index(op.f('ix_risk_events_ts'), 'risk_events', ['ts'], unique=False)

    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('qty', sa.Integer(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('opened_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('instrument_type', sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trades_id'), 'trades', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trades_id'), table_name='trades')
    op.drop_table('trades')
    op.drop_index(op.f('ix_risk_events_ts'), table_name='risk_events')
    op.drop_index(op.f('ix_risk_events_id'), table_name='risk_events')
    op.drop_table('risk_events')
    op.drop_index(op.f('ix_risk_config_key'), table_name='risk_config')
    op.drop_index(op.f('ix_risk_config_id'), table_name='risk_config')
    op.drop_table('risk_config')
    op.drop_index(op.f('ix_positions_snapshot_ts'), table_name='positions_snapshot')
    op.drop_index(op.f('ix_positions_snapshot_id'), table_name='positions_snapshot')
    op.drop_table('positions_snapshot')
    op.drop_index(op.f('ix_daily_summary_id'), table_name='daily_summary')
    op.drop_index(op.f('ix_daily_summary_date'), table_name='daily_summary')
    op.drop_table('daily_summary')
