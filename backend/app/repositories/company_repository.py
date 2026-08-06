from __future__ import annotations

import uuid
from sqlalchemy import or_, select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.models.company import Company
from app.models.financials import KeyRatio
from app.repositories.base_repository import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Company, session)

    async def get_by_nse_symbol(self, symbol: str) -> Company | None:
        result = await self.session.execute(
            select(Company).where(Company.nse_symbol == symbol.upper())
        )
        return result.scalar_one_or_none()

    async def get_by_bse_code(self, code: str) -> Company | None:
        result = await self.session.execute(
            select(Company).where(Company.bse_code == code)
        )
        return result.scalar_one_or_none()

    async def get_by_symbol_or_code(self, identifier: str) -> Company | None:
        """Try NSE symbol first, then BSE code."""
        result = await self.session.execute(
            select(Company).where(
                or_(
                    Company.nse_symbol == identifier.upper(),
                    Company.bse_code == identifier,
                )
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[Company], int]:
        """
        Full-text search on company name, NSE symbol, BSE code.
        Returns (results, total_count).
        """
        search_filter = or_(
            Company.name.ilike(f"%{query}%"),
            Company.nse_symbol.ilike(f"{query}%"),
            Company.bse_code.ilike(f"{query}%"),
        )

        count_result = await self.session.execute(
            select(func.count()).select_from(Company).where(search_filter)
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(Company)
            .where(search_filter)
            .order_by(Company.market_cap_cr.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        companies = list(result.scalars().all())

        return companies, total

    async def get_by_sector(
        self,
        sector: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Company]:
        result = await self.session.execute(
            select(Company)
            .where(Company.sector == sector)
            .order_by(Company.market_cap_cr.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_peers(self, company: Company, limit: int = 10) -> list[tuple]:
        """
        Get peer companies in the same industry with latest annual key ratios.
        Excludes the company itself.
        """
        industry_filter = (
            Company.industry == company.industry
            if company.industry
            else Company.sector == (company.sector or "")
        )

        # Subquery: latest annual ratio year per company
        latest_sq = (
            select(
                KeyRatio.company_id,
                func.max(KeyRatio.period_year).label("latest_year"),
            )
            .where(KeyRatio.period_type == "annual")
            .group_by(KeyRatio.company_id)
            .subquery()
        )

        result = await self.session.execute(
            select(
                Company.id,
                Company.name,
                Company.nse_symbol,
                Company.bse_code,
                Company.sector,
                Company.industry,
                Company.market_cap_cr,
                Company.cmp,
                Company.promoter_holding_pct,
                KeyRatio.pe_ratio,
                KeyRatio.pb_ratio,
                KeyRatio.roe_pct,
                KeyRatio.roce_pct,
                KeyRatio.net_profit_margin_pct,
                KeyRatio.debt_equity_ratio,
                KeyRatio.revenue_growth_pct,
            )
            .outerjoin(latest_sq, Company.id == latest_sq.c.company_id)
            .outerjoin(
                KeyRatio,
                and_(
                    KeyRatio.company_id == Company.id,
                    KeyRatio.period_year == latest_sq.c.latest_year,
                    KeyRatio.period_type == "annual",
                ),
            )
            .where(industry_filter, Company.id != company.id)
            .order_by(Company.market_cap_cr.desc().nullslast())
            .limit(limit)
        )
        return list(result.all())
