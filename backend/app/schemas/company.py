from __future__ import annotations

import uuid
from decimal import Decimal
from pydantic import BaseModel, Field


class CompanySearchResult(BaseModel):
    id: uuid.UUID
    name: str
    nse_symbol: str | None
    bse_code: str | None
    sector: str | None
    industry: str | None
    market_cap_cr: Decimal | None
    cmp: Decimal | None

    model_config = {"from_attributes": True}


class CompanyBrief(CompanySearchResult):
    """Compact company representation for lists and peer comparison."""
    promoter_holding_pct: Decimal | None
    isin: str | None


class CompanyDetail(CompanyBrief):
    """Full company profile for the company overview page."""
    description: str | None
    website: str | None
    founded_year: int | None
    headquarters: str | None
    employee_count: int | None
    fii_holding_pct: Decimal | None
    dii_holding_pct: Decimal | None
    public_holding_pct: Decimal | None
    face_value: Decimal | None

    model_config = {"from_attributes": True}


class CompanyCreate(BaseModel):
    """Used by the data pipeline to create/update company records."""
    name: str = Field(max_length=255)
    nse_symbol: str | None = Field(default=None, max_length=50)
    bse_code: str | None = Field(default=None, max_length=20)
    isin: str | None = Field(default=None, max_length=12)
    sector: str | None = None
    industry: str | None = None
    market_cap_cr: Decimal | None = None
    face_value: Decimal | None = None
    cmp: Decimal | None = None
    promoter_holding_pct: Decimal | None = None


class PeerCompanyItem(BaseModel):
    """Used in peer comparison panel."""
    id: uuid.UUID
    name: str
    nse_symbol: str | None
    bse_code: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap_cr: Decimal | None
    cmp: Decimal | None = None
    promoter_holding_pct: Decimal | None = None
    # Latest annual key ratios
    pe_ratio: Decimal | None = None
    pb_ratio: Decimal | None = None
    roe_pct: Decimal | None = None
    roce_pct: Decimal | None = None
    net_profit_margin_pct: Decimal | None = None
    debt_equity_ratio: Decimal | None = None
    revenue_growth_pct: Decimal | None = None

    model_config = {"from_attributes": True}


class ScreenerResult(BaseModel):
    """Company row returned by the screener — base fields + latest key ratios."""
    id: uuid.UUID
    name: str
    nse_symbol: str | None
    sector: str | None
    industry: str | None
    market_cap_cr: Decimal | None
    cmp: Decimal | None
    promoter_holding_pct: Decimal | None
    # — Valuation
    pe_ratio: Decimal | None = None
    pb_ratio: Decimal | None = None
    # — Profitability
    roe_pct: Decimal | None = None
    roce_pct: Decimal | None = None
    net_profit_margin_pct: Decimal | None = None
    ebitda_margin_pct: Decimal | None = None
    # — Health
    debt_equity_ratio: Decimal | None = None
    interest_coverage: Decimal | None = None
    current_ratio: Decimal | None = None
    # — Growth
    revenue_growth_pct: Decimal | None = None
    pat_growth_pct: Decimal | None = None
    # — Dividend
    dividend_yield_pct: Decimal | None = None

    model_config = {"from_attributes": True}
