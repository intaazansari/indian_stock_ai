"""add week52 high/low to companies

Revision ID: 4c7a2b9e1f03
Revises: 11468eabb117
Create Date: 2026-08-05 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "4c7a2b9e1f03"
down_revision: Union[str, None] = "11468eabb117"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column(
            "week52_high",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
            comment="52-week high price",
        ),
    )
    op.add_column(
        "companies",
        sa.Column(
            "week52_low",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
            comment="52-week low price",
        ),
    )


def downgrade() -> None:
    op.drop_column("companies", "week52_low")
    op.drop_column("companies", "week52_high")
