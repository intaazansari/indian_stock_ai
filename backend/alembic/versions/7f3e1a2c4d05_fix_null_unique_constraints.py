"""fix_null_unique_constraints

Replaces the UNIQUE constraints on (company_id, period_type, period_year, period_quarter)
for income_statements, balance_sheets and cash_flows with ones that treat NULL as equal
(PostgreSQL 15+ NULLS NOT DISTINCT), so annual rows (period_quarter IS NULL) are properly
deduplicated by ON CONFLICT DO UPDATE.

Also removes any duplicate rows created before this fix.

Revision ID: 7f3e1a2c4d05
Revises: 4c7a2b9e1f03
Create Date: 2026-08-05 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7f3e1a2c4d05"
down_revision: Union[str, None] = "4c7a2b9e1f03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    for table, constraint in [
        ("income_statements", "uq_income_period"),
        ("balance_sheets", "uq_balance_period"),
        ("cash_flows", "uq_cashflow_period"),
    ]:
        # 1. Remove duplicates – keep the row with the latest updated_at per key
        dedup_sql = sa.text(f"""
            DELETE FROM {table}
            WHERE id NOT IN (
                SELECT DISTINCT ON (company_id, period_type, period_year, period_quarter) id
                FROM {table}
                ORDER BY company_id, period_type, period_year, period_quarter, updated_at DESC
            )
        """)
        conn.execute(dedup_sql)

        # 2. Drop the old constraint (NULL != NULL, so it never fires for annual rows)
        op.drop_constraint(constraint, table, type_="unique")

        # 3. Re-create with NULLS NOT DISTINCT (PostgreSQL 15+) so NULL == NULL
        op.create_unique_constraint(
            constraint,
            table,
            ["company_id", "period_type", "period_year", "period_quarter"],
            postgresql_nulls_not_distinct=True,
        )


def downgrade() -> None:
    for table, constraint in [
        ("income_statements", "uq_income_period"),
        ("balance_sheets", "uq_balance_period"),
        ("cash_flows", "uq_cashflow_period"),
    ]:
        op.drop_constraint(constraint, table, type_="unique")
        op.create_unique_constraint(
            constraint,
            table,
            ["company_id", "period_type", "period_year", "period_quarter"],
        )
