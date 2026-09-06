"""add market_movers table

Revision ID: 9a1d3f6c2b81
Revises: 7f3e1a2c4d05
Create Date: 2026-09-06 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9a1d3f6c2b81"
down_revision: Union[str, None] = "7f3e1a2c4d05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_movers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("close", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("previous_close", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("change_pct", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", "symbol", "type", name="uq_market_mover_date_symbol_type"),
    )
    op.create_index(op.f("ix_market_movers_date"), "market_movers", ["date"], unique=False)
    op.create_index(op.f("ix_market_movers_symbol"), "market_movers", ["symbol"], unique=False)
    op.create_index(op.f("ix_market_movers_type"), "market_movers", ["type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_market_movers_type"), table_name="market_movers")
    op.drop_index(op.f("ix_market_movers_symbol"), table_name="market_movers")
    op.drop_index(op.f("ix_market_movers_date"), table_name="market_movers")
    op.drop_table("market_movers")
