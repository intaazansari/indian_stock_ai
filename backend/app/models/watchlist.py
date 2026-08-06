"""Watchlist and Portfolio ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Watchlist(Base, TimestampMixin):
    """
    A user's watchlist entry for a company.

    One user can add the same company only once (UniqueConstraint).
    """
    __tablename__ = "watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_watchlist_user_company"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="watchlist_items")  # noqa: F821
    company: Mapped["Company"] = relationship("Company", back_populates="watchlist_items")  # noqa: F821


class Portfolio(Base, TimestampMixin):
    """
    A user's portfolio holding in a company.

    Supports multiple lots (buy_price + quantity per entry).
    Aggregation is done at the service layer.
    """
    __tablename__ = "portfolio"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    buy_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    buy_date: Mapped[datetime | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="portfolio_holdings")  # noqa: F821
    company: Mapped["Company"] = relationship("Company")
