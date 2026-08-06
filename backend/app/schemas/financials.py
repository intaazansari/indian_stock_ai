from __future__ import annotations

import uuid
from decimal import Decimal
from pydantic import BaseModel


class IncomeStatementItem(BaseModel):
    period_year: int
    period_type: str
    period_quarter: int | None
    revenue_cr: Decimal | None
    ebitda_cr: Decimal | None
    ebitda_margin_pct: Decimal | None = None
    pat_cr: Decimal | None
    net_profit_margin_pct: Decimal | None = None
    eps_basic: Decimal | None
    eps_diluted: Decimal | None
    dividend_per_share: Decimal | None

    model_config = {"from_attributes": True}


class BalanceSheetItem(BaseModel):
    period_year: int
    period_type: str
    total_assets_cr: Decimal | None
    shareholders_equity_cr: Decimal | None
    long_term_debt_cr: Decimal | None
    short_term_debt_cr: Decimal | None
    cash_cr: Decimal | None
    receivables_cr: Decimal | None
    inventories_cr: Decimal | None

    model_config = {"from_attributes": True}


class CashFlowItem(BaseModel):
    period_year: int
    period_type: str
    cfo_cr: Decimal | None
    cfi_cr: Decimal | None
    cff_cr: Decimal | None
    capex_cr: Decimal | None
    free_cash_flow_cr: Decimal | None

    model_config = {"from_attributes": True}


class KeyRatioItem(BaseModel):
    period_year: int
    period_type: str
    roe_pct: Decimal | None
    roce_pct: Decimal | None
    roa_pct: Decimal | None
    ebitda_margin_pct: Decimal | None
    net_profit_margin_pct: Decimal | None
    pe_ratio: Decimal | None
    pb_ratio: Decimal | None
    ev_ebitda: Decimal | None
    debt_equity_ratio: Decimal | None
    current_ratio: Decimal | None
    interest_coverage: Decimal | None
    revenue_growth_pct: Decimal | None
    pat_growth_pct: Decimal | None
    cash_conversion_cycle: Decimal | None

    model_config = {"from_attributes": True}


class FinancialSummary(BaseModel):
    """All financial statements combined — used by the company financials page."""
    company_id: uuid.UUID
    income_statements: list[IncomeStatementItem]
    balance_sheets: list[BalanceSheetItem]
    cash_flows: list[CashFlowItem]
    key_ratios: list[KeyRatioItem]
