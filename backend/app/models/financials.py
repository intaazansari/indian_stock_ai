"""
Financial statement ORM models.

Four tables:
  - IncomeStatement   (P&L)
  - BalanceSheet
  - CashFlow
  - KeyRatio          (derived metrics, precomputed for query performance)

Design notes:
  - period_type: "annual" | "quarterly"
  - period_year: fiscal year (April–March for India)
  - period_quarter: Q1/Q2/Q3/Q4 (null for annual)
  - All monetary values stored in crores (₹ Cr) — standard Indian notation.
  - Nullable fields because older filings may have gaps.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from sqlalchemy import ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class IncomeStatement(Base, TimestampMixin):
    __tablename__ = "income_statements"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "period_type", "period_year", "period_quarter",
            name="uq_income_period",
        ),
        Index("ix_income_company_period", "company_id", "period_year", "period_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)   # annual | quarterly
    period_year: Mapped[int] = mapped_column(nullable=False)               # Fiscal year (e.g. 2024)
    period_quarter: Mapped[int | None] = mapped_column(nullable=True)      # 1-4 or null

    # ── Revenue ───────────────────────────────────────────────────────────────
    revenue_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    other_income_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    total_income_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

    # ── Expenses ──────────────────────────────────────────────────────────────
    raw_material_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    employee_cost_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    other_expenses_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    total_expenses_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

    # ── Profitability ─────────────────────────────────────────────────────────
    ebitda_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    depreciation_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    ebit_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    interest_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    pbt_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    tax_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    pat_cr: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True, comment="Profit After Tax"
    )
    minority_interest_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    pat_after_minority_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

    # ── Per Share ─────────────────────────────────────────────────────────────
    eps_basic: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    eps_diluted: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    dividend_per_share: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="income_statements")  # noqa: F821


class BalanceSheet(Base, TimestampMixin):
    __tablename__ = "balance_sheets"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "period_type", "period_year", "period_quarter",
            name="uq_balance_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)
    period_year: Mapped[int] = mapped_column(nullable=False)
    period_quarter: Mapped[int | None] = mapped_column(nullable=True)

    # ── Assets ────────────────────────────────────────────────────────────────
    total_assets_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    fixed_assets_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    current_assets_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    cash_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    inventories_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    receivables_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    investments_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

    # ── Liabilities ───────────────────────────────────────────────────────────
    total_liabilities_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    long_term_debt_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    short_term_debt_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    current_liabilities_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    trade_payables_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

    # ── Equity ────────────────────────────────────────────────────────────────
    shareholders_equity_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    share_capital_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    reserves_surplus_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="balance_sheets")  # noqa: F821


class CashFlow(Base, TimestampMixin):
    __tablename__ = "cash_flows"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "period_type", "period_year", "period_quarter",
            name="uq_cashflow_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)
    period_year: Mapped[int] = mapped_column(nullable=False)
    period_quarter: Mapped[int | None] = mapped_column(nullable=True)

    # ── Cash Flows ────────────────────────────────────────────────────────────
    cfo_cr: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True, comment="Cash Flow from Operations"
    )
    cfi_cr: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True, comment="Cash Flow from Investing"
    )
    cff_cr: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True, comment="Cash Flow from Financing"
    )
    capex_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    free_cash_flow_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    net_change_in_cash_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="cash_flows")  # noqa: F821


class KeyRatio(Base, TimestampMixin):
    """
    Precomputed key financial ratios.

    Precomputing avoids repeated heavy calculations in queries.
    Refreshed by a Celery task whenever underlying financials are updated.
    """
    __tablename__ = "key_ratios"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "period_type", "period_year",
            name="uq_ratio_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)
    period_year: Mapped[int] = mapped_column(nullable=False)

    # ── Profitability ─────────────────────────────────────────────────────────
    roe_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    roce_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    roa_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    ebitda_margin_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    net_profit_margin_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    # ── Valuation ─────────────────────────────────────────────────────────────
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    pb_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    ps_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    ev_ebitda: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    ev_sales: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    dividend_yield_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    # ── Financial Health ──────────────────────────────────────────────────────
    debt_equity_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    current_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    quick_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    interest_coverage: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # ── Efficiency ────────────────────────────────────────────────────────────
    asset_turnover: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    inventory_days: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    receivables_days: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    payables_days: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    cash_conversion_cycle: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # ── Growth (YoY %) ────────────────────────────────────────────────────────
    revenue_growth_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    pat_growth_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    eps_growth_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="key_ratios")  # noqa: F821
