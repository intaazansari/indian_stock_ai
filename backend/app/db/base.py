"""
SQLAlchemy declarative base and shared mixins.

All ORM models import from here — never create a separate Base.
TimestampMixin provides created_at / updated_at on every model.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, mapped_column


class Base(DeclarativeBase):
    """Single declarative base for all ORM models."""
    pass


class TimestampMixin:
    """Automatically managed created_at and updated_at timestamps (UTC)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
