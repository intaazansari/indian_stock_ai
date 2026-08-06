from __future__ import annotations

import uuid

from sqlalchemy import nullslast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financials import BalanceSheet, CashFlow, IncomeStatement, KeyRatio
from app.repositories.base_repository import BaseRepository


class FinancialRepository:
    """
    Specialised repository for financial statement queries.
    Not a generic BaseRepository because financial queries are complex.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_income_statements(
        self,
        company_id: uuid.UUID,
        period_type: str = "annual",
        years: int = 10,
    ) -> list[IncomeStatement]:
        result = await self.session.execute(
            select(IncomeStatement)
            .where(
                IncomeStatement.company_id == company_id,
                IncomeStatement.period_type == period_type,
            )
            .order_by(
                IncomeStatement.period_year.desc(),
                nullslast(IncomeStatement.period_quarter.desc()),
            )
            .limit(years)
        )
        return list(result.scalars().all())

    async def get_balance_sheets(
        self,
        company_id: uuid.UUID,
        period_type: str = "annual",
        years: int = 10,
    ) -> list[BalanceSheet]:
        result = await self.session.execute(
            select(BalanceSheet)
            .where(
                BalanceSheet.company_id == company_id,
                BalanceSheet.period_type == period_type,
            )
            .order_by(
                BalanceSheet.period_year.desc(),
                nullslast(BalanceSheet.period_quarter.desc()),
            )
            .limit(years)
        )
        return list(result.scalars().all())

    async def get_cash_flows(
        self,
        company_id: uuid.UUID,
        period_type: str = "annual",
        years: int = 10,
    ) -> list[CashFlow]:
        result = await self.session.execute(
            select(CashFlow)
            .where(
                CashFlow.company_id == company_id,
                CashFlow.period_type == period_type,
            )
            .order_by(
                CashFlow.period_year.desc(),
                nullslast(CashFlow.period_quarter.desc()),
            )
            .limit(years)
        )
        return list(result.scalars().all())

    async def get_key_ratios(
        self,
        company_id: uuid.UUID,
        period_type: str = "annual",
        years: int = 10,
    ) -> list[KeyRatio]:
        result = await self.session.execute(
            select(KeyRatio)
            .where(
                KeyRatio.company_id == company_id,
                KeyRatio.period_type == period_type,
            )
            .order_by(
                KeyRatio.period_year.desc(),
            )
            .limit(years)
        )
        return list(result.scalars().all())

    async def get_latest_key_ratios(self, company_id: uuid.UUID) -> KeyRatio | None:
        result = await self.session.execute(
            select(KeyRatio)
            .where(
                KeyRatio.company_id == company_id,
                KeyRatio.period_type == "annual",
            )
            .order_by(KeyRatio.period_year.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
