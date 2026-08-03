"""create paper_orders table

Revision ID: 002_paper_orders
Revises: 001_initial
Create Date: 2026-08-04

Adds the paper_orders table for PaperBrokerAdapter order logging.
All writes made while PAPER_MODE=True are logged here; no real orders
are ever sent to Angel One.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "002_paper_orders"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_orders",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("ts", sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("transaction_type", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("price", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("product_type", sa.String(20), nullable=False),
        sa.Column("symbol_token", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PAPER_COMPLETE"),
        sa.Column("fill_price", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("paper_orders")
