"""
MarketMover ORM model.

Stores the daily Top Gainers / Top Losers snapshot computed after NSE market
close (Mon-Fri, excluding NSE holidays). One row per (date, symbol, type).

Populated by `scripts/refresh_prices.py`, which is run daily via the
"Daily Price Refresh" GitHub Actions workflow.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Date, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MarketMover(Base, TimestampMixin):
    """A single Top Gainer/Loser row for a given trading date."""

    __tablename__ = "market_movers"
    __table_args__ = (
        UniqueConstraint("date", "symbol", "type", name="uq_market_mover_date_symbol_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    date: Mapped["Date"] = mapped_column(Date, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False)

    close: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    previous_close: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    change_pct: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)

    # "gainer" or "loser"
    type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # 1-based rank within its (date, type) group — 1 is the biggest gainer/loser.
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<MarketMover {self.date} {self.symbol} {self.type} {self.change_pct}%>"
