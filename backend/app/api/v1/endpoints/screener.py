"""
Screener endpoint — filters companies by financial criteria.

Joins `companies` with the latest annual `key_ratios` row per company.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Body
from sqlalchemy import select, func, and_, or_, desc, asc, nullslast

from app.core.dependencies import DBSession
from app.models.company import Company
from app.models.financials import KeyRatio
from app.schemas.common import PaginatedResponse
from app.schemas.company import ScreenerResult
from pydantic import BaseModel, Field

router = APIRouter()


class ScreenerFilter(BaseModel):
    """Structured screener filters. All fields are optional."""

    # Classification
    sector: str | None = None
    industry: str | None = None

    # Market cap (₹ Cr)
    market_cap_min: Decimal | None = None
    market_cap_max: Decimal | None = None

    # Valuation
    pe_min: Decimal | None = None
    pe_max: Decimal | None = None
    pb_min: Decimal | None = None
    pb_max: Decimal | None = None

    # Profitability
    roe_min: Decimal | None = None
    roce_min: Decimal | None = None
    net_profit_margin_min: Decimal | None = None

    # Financial health
    debt_equity_max: Decimal | None = None
    current_ratio_min: Decimal | None = None

    # Growth
    revenue_growth_min: Decimal | None = None
    pat_growth_min: Decimal | None = None

    # Ownership
    promoter_holding_min: Decimal | None = None

    # Sorting
    sort_by: Literal[
        "market_cap", "pe_ratio", "pb_ratio", "roe_pct", "roce_pct",
        "revenue_growth_pct", "pat_growth_pct", "debt_equity_ratio",
        "net_profit_margin_pct", "dividend_yield_pct",
    ] = "market_cap"
    sort_order: Literal["asc", "desc"] = "desc"

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


_SORT_COL = {
    "market_cap":            Company.market_cap_cr,
    "pe_ratio":              KeyRatio.pe_ratio,
    "pb_ratio":              KeyRatio.pb_ratio,
    "roe_pct":               KeyRatio.roe_pct,
    "roce_pct":              KeyRatio.roce_pct,
    "revenue_growth_pct":    KeyRatio.revenue_growth_pct,
    "pat_growth_pct":        KeyRatio.pat_growth_pct,
    "debt_equity_ratio":     KeyRatio.debt_equity_ratio,
    "net_profit_margin_pct": KeyRatio.net_profit_margin_pct,
    "dividend_yield_pct":    KeyRatio.dividend_yield_pct,
}


async def _run_screener(db, filters: ScreenerFilter) -> tuple[list[ScreenerResult], int]:
    # Latest annual ratio year per company
    latest_sq = (
        select(
            KeyRatio.company_id,
            func.max(KeyRatio.period_year).label("latest_year"),
        )
        .where(KeyRatio.period_type == "annual")
        .group_by(KeyRatio.company_id)
        .subquery()
    )

    stmt = (
        select(
            Company.id,
            Company.name,
            Company.nse_symbol,
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
            KeyRatio.ebitda_margin_pct,
            KeyRatio.debt_equity_ratio,
            KeyRatio.interest_coverage,
            KeyRatio.current_ratio,
            KeyRatio.revenue_growth_pct,
            KeyRatio.pat_growth_pct,
            KeyRatio.dividend_yield_pct,
        )
        .join(latest_sq, Company.id == latest_sq.c.company_id)
        .join(
            KeyRatio,
            and_(
                KeyRatio.company_id == Company.id,
                KeyRatio.period_year == latest_sq.c.latest_year,
                KeyRatio.period_type == "annual",
            ),
        )
    )

    conds: list = []
    if filters.sector:
        conds.append(Company.sector == filters.sector)
    if filters.industry:
        conds.append(Company.industry == filters.industry)
    if filters.market_cap_min is not None:
        conds.append(Company.market_cap_cr >= filters.market_cap_min)
    if filters.market_cap_max is not None:
        conds.append(Company.market_cap_cr <= filters.market_cap_max)
    if filters.pe_min is not None:
        conds.append(KeyRatio.pe_ratio >= filters.pe_min)
    if filters.pe_max is not None:
        conds.append(and_(KeyRatio.pe_ratio <= filters.pe_max, KeyRatio.pe_ratio > 0))
    if filters.pb_min is not None:
        conds.append(KeyRatio.pb_ratio >= filters.pb_min)
    if filters.pb_max is not None:
        conds.append(KeyRatio.pb_ratio <= filters.pb_max)
    if filters.roe_min is not None:
        conds.append(KeyRatio.roe_pct >= filters.roe_min)
    if filters.roce_min is not None:
        conds.append(KeyRatio.roce_pct >= filters.roce_min)
    if filters.net_profit_margin_min is not None:
        conds.append(KeyRatio.net_profit_margin_pct >= filters.net_profit_margin_min)
    if filters.debt_equity_max is not None:
        conds.append(
            or_(KeyRatio.debt_equity_ratio <= filters.debt_equity_max,
                KeyRatio.debt_equity_ratio == None)  # noqa: E711
        )
    if filters.current_ratio_min is not None:
        conds.append(KeyRatio.current_ratio >= filters.current_ratio_min)
    if filters.revenue_growth_min is not None:
        conds.append(KeyRatio.revenue_growth_pct >= filters.revenue_growth_min)
    if filters.pat_growth_min is not None:
        conds.append(KeyRatio.pat_growth_pct >= filters.pat_growth_min)
    if filters.promoter_holding_min is not None:
        conds.append(Company.promoter_holding_pct >= filters.promoter_holding_min)

    if conds:
        stmt = stmt.where(and_(*conds))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()

    sort_col = _SORT_COL.get(filters.sort_by, Company.market_cap_cr)
    direction = desc if filters.sort_order == "desc" else asc
    stmt = stmt.order_by(nullslast(direction(sort_col)))
    stmt = stmt.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)

    rows = await db.execute(stmt)
    items = [ScreenerResult(**dict(r._mapping)) for r in rows]
    return items, total


@router.get("/sectors", response_model=list[str])
async def list_sectors(db: DBSession) -> list[str]:
    """Distinct sectors for the filter dropdown."""
    rows = await db.execute(
        select(Company.sector)
        .where(Company.sector != None)  # noqa: E711
        .distinct()
        .order_by(Company.sector)
    )
    return [r[0] for r in rows if r[0]]


@router.post("/filter", response_model=PaginatedResponse[ScreenerResult])
async def screen_companies(
    db: DBSession,
    filters: ScreenerFilter = Body(...),
) -> PaginatedResponse[ScreenerResult]:
    """Filter companies by financial criteria."""
    items, total = await _run_screener(db, filters)
    return PaginatedResponse(
        items=items,
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        total_pages=max(1, -(-total // filters.page_size)),
    )
