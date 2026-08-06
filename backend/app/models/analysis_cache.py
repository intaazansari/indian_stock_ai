"""
AI Analysis Cache model.

Stores pre-computed AI analysis results per company per agent.

Design notes:
  - agent_type maps to each agent class (research, financial, quality, etc.)
  - analysis_json stores the structured agent output.
  - is_stale flags records that need refresh (e.g., after new quarterly results).
  - version tracks the prompt/model version used so we can re-run on upgrades.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class AnalysisCache(Base, TimestampMixin):
    __tablename__ = "analysis_cache"
    __table_args__ = (
        Index("ix_analysis_company_agent", "company_id", "agent_type"),
        Index("ix_analysis_stale", "is_stale", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )

    # ── Analysis Metadata ─────────────────────────────────────────────────────
    agent_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="research | financial | quality | valuation | risk | management | quarterly | summary"
    )
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    period_year: Mapped[int | None] = mapped_column(nullable=True, comment="Fiscal year context")
    period_quarter: Mapped[int | None] = mapped_column(nullable=True)

    # ── Analysis Output ───────────────────────────────────────────────────────
    analysis_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── State ─────────────────────────────────────────────────────────────────
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="analysis_cache")  # noqa: F821

    def __repr__(self) -> str:
        return f"<AnalysisCache company={self.company_id} agent={self.agent_type}>"
