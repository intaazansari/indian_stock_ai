"""
Company ORM model.

Represents a publicly listed Indian company (BSE/NSE).

Design notes:
  - nse_symbol and bse_code are both nullable because some companies
    are listed on only one exchange.
  - sector / industry follows the standard Indian classification.
  - market_cap_cr stores value in crores (standard Indian notation).
  - promoter_holding_pct is stored as a decimal (e.g. 72.45 for 72.45%).
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Company(Base, TimestampMixin):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("nse_symbol", name="uq_company_nse_symbol"),
        UniqueConstraint("bse_code", name="uq_company_bse_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nse_symbol: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    bse_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True, unique=True)

    # ── Classification ────────────────────────────────────────────────────────
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    sub_industry: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Market Data ───────────────────────────────────────────────────────────
    market_cap_cr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    face_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    cmp: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="Current Market Price"
    )

    # ── Ownership ─────────────────────────────────────────────────────────────
    promoter_holding_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    fii_holding_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    dii_holding_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    public_holding_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # ── Company Details ───────────────────────────────────────────────────────
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    founded_year: Mapped[int | None] = mapped_column(nullable=True)
    headquarters: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_count: Mapped[int | None] = mapped_column(nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    income_statements: Mapped[list["IncomeStatement"]] = relationship(  # noqa: F821
        "IncomeStatement", back_populates="company", cascade="all, delete-orphan"
    )
    balance_sheets: Mapped[list["BalanceSheet"]] = relationship(  # noqa: F821
        "BalanceSheet", back_populates="company", cascade="all, delete-orphan"
    )
    cash_flows: Mapped[list["CashFlow"]] = relationship(  # noqa: F821
        "CashFlow", back_populates="company", cascade="all, delete-orphan"
    )
    key_ratios: Mapped[list["KeyRatio"]] = relationship(  # noqa: F821
        "KeyRatio", back_populates="company", cascade="all, delete-orphan"
    )
    analysis_cache: Mapped[list["AnalysisCache"]] = relationship(  # noqa: F821
        "AnalysisCache", back_populates="company", cascade="all, delete-orphan"
    )
    watchlist_items: Mapped[list["Watchlist"]] = relationship(  # noqa: F821
        "Watchlist", back_populates="company"
    )

    def __repr__(self) -> str:
        return f"<Company name={self.name} nse={self.nse_symbol}>"
