from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.financial_repository import FinancialRepository
from app.schemas.financials import (
    BalanceSheetItem,
    CashFlowItem,
    FinancialSummary,
    IncomeStatementItem,
    KeyRatioItem,
)


class FinancialService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = FinancialRepository(session)

    @staticmethod
    def _dedup_by_year(records: list) -> list:
        """Keep only the first (latest) record per fiscal year. Used for annual data."""
        seen: set[int] = set()
        deduped = []
        for r in records:
            if r.period_year not in seen:
                seen.add(r.period_year)
                deduped.append(r)
        return deduped

    @staticmethod
    def _dedup_by_period(records: list) -> list:
        """Keep only the first record per (year, quarter) pair. Used for quarterly data."""
        seen: set[tuple] = set()
        deduped = []
        for r in records:
            key = (r.period_year, getattr(r, "period_quarter", None))
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        return deduped

    async def get_financial_summary(
        self,
        company_id: uuid.UUID,
        period_type: str = "annual",
        years: int = 10,
    ) -> FinancialSummary:
        # For quarterly: request more rows (4 per year) and deduplicate by period.
        # For annual: same dedup-by-year logic as before.
        fetch_limit = years * 5 if period_type == "quarterly" else years * 2
        dedup = self._dedup_by_period if period_type == "quarterly" else self._dedup_by_year

        income_stmts = dedup(
            await self.repo.get_income_statements(company_id, period_type, fetch_limit)
        )[:years]
        balance_sheets = dedup(
            await self.repo.get_balance_sheets(company_id, period_type, fetch_limit)
        )[:years]
        cash_flows = dedup(
            await self.repo.get_cash_flows(company_id, period_type, fetch_limit)
        )[:years]
        key_ratios = dedup(
            await self.repo.get_key_ratios(company_id, period_type, fetch_limit)
        )[:years]

        return FinancialSummary(
            company_id=company_id,
            income_statements=[IncomeStatementItem.model_validate(r) for r in income_stmts],
            balance_sheets=[BalanceSheetItem.model_validate(r) for r in balance_sheets],
            cash_flows=[CashFlowItem.model_validate(r) for r in cash_flows],
            key_ratios=[KeyRatioItem.model_validate(r) for r in key_ratios],
        )
