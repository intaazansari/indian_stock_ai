from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CompanyNotFoundError
from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.schemas.company import CompanyDetail, CompanySearchResult, PeerCompanyItem
from app.schemas.common import PaginatedResponse, PaginationParams


class CompanyService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = CompanyRepository(session)

    async def get_by_symbol(self, symbol: str) -> Company:
        company = await self.repo.get_by_symbol_or_code(symbol)
        if not company:
            raise CompanyNotFoundError(f"Company with symbol '{symbol}' not found")
        return company

    async def get_by_id(self, company_id: uuid.UUID) -> Company:
        company = await self.repo.get_by_id(company_id)
        if not company:
            raise CompanyNotFoundError()
        return company

    async def search(
        self,
        query: str,
        params: PaginationParams,
    ) -> PaginatedResponse[CompanySearchResult]:
        companies, total = await self.repo.search(
            query=query,
            limit=params.page_size,
            offset=params.offset,
        )
        items = [CompanySearchResult.model_validate(c) for c in companies]
        return PaginatedResponse.create(items=items, total=total, params=params)

    async def get_peers(self, symbol: str) -> list[PeerCompanyItem]:
        company = await self.get_by_symbol(symbol)
        rows = await self.repo.get_peers(company)
        return [
            PeerCompanyItem(
                id=r.id,
                name=r.name,
                nse_symbol=r.nse_symbol,
                bse_code=r.bse_code,
                sector=r.sector,
                industry=r.industry,
                market_cap_cr=r.market_cap_cr,
                cmp=r.cmp,
                promoter_holding_pct=r.promoter_holding_pct,
                pe_ratio=r.pe_ratio,
                pb_ratio=r.pb_ratio,
                roe_pct=r.roe_pct,
                roce_pct=r.roce_pct,
                net_profit_margin_pct=r.net_profit_margin_pct,
                debt_equity_ratio=r.debt_equity_ratio,
                revenue_growth_pct=r.revenue_growth_pct,
            )
            for r in rows
        ]
