"""
User ORM model.

Design notes:
  - Email is the unique identifier (not username).
  - Password is always stored hashed. Raw password never persists.
  - is_active flag for soft account suspension.
  - is_verified flag for email verification flow.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    watchlist_items: Mapped[list["Watchlist"]] = relationship(  # noqa: F821
        "Watchlist", back_populates="user", cascade="all, delete-orphan"
    )
    portfolio_holdings: Mapped[list["Portfolio"]] = relationship(  # noqa: F821
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
