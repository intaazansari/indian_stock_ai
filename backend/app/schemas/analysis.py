"""
Pydantic schemas for AI analysis outputs.

Each agent returns a typed, structured response — never raw strings.
This allows the frontend to render rich UI instead of just displaying text.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum
from pydantic import BaseModel, Field


class SentimentLevel(StrEnum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScoreItem(BaseModel):
    label: str
    score: int = Field(ge=0, le=10)
    explanation: str


class QualityScoreResponse(BaseModel):
    """Output of BusinessQualityAgent."""
    company_id: uuid.UUID
    overall_score: int = Field(ge=0, le=10)
    business_quality: ScoreItem
    financial_health: ScoreItem
    management_quality: ScoreItem
    growth_quality: ScoreItem
    valuation: ScoreItem
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    agent_type: str = "quality"
    model_used: str
    generated_at: str


class FinancialInsight(BaseModel):
    title: str
    insight: str
    sentiment: SentimentLevel
    metric_value: str | None = None


class FinancialAnalysisResponse(BaseModel):
    """Output of FinancialAnalysisAgent."""
    company_id: uuid.UUID
    period_year: int
    revenue_trend: str
    profitability_trend: str
    balance_sheet_health: str
    cash_flow_quality: str
    key_insights: list[FinancialInsight]
    red_flags: list[str]
    positives: list[str]
    agent_type: str = "financial"
    model_used: str
    generated_at: str


class RedFlag(BaseModel):
    title: str
    description: str
    severity: RiskLevel
    category: str  # accounting | governance | business | financial


class RiskAnalysisResponse(BaseModel):
    """Output of RiskAgent."""
    company_id: uuid.UUID
    overall_risk_level: RiskLevel
    red_flags: list[RedFlag]
    business_risks: list[str]
    financial_risks: list[str]
    governance_risks: list[str]
    regulatory_risks: list[str]
    agent_type: str = "risk"
    model_used: str
    generated_at: str


class ValuationAnalysisResponse(BaseModel):
    """Output of ValuationAgent."""
    company_id: uuid.UUID
    current_pe: Decimal | None
    sector_median_pe: Decimal | None
    historical_pe_median: Decimal | None
    valuation_commentary: str
    is_overvalued: bool | None
    fair_value_estimate: Decimal | None
    upside_downside_pct: Decimal | None
    valuation_methodology: str
    key_assumptions: list[str]
    agent_type: str = "valuation"
    model_used: str
    generated_at: str


class ExecutiveSummaryResponse(BaseModel):
    """
    Output of ExecutiveSummaryAgent.

    This is the primary summary card shown at the top of every company page.
    It synthesises inputs from multiple agents into a concise investor brief.
    """
    company_id: uuid.UUID
    one_liner: str = Field(description="Single sentence describing what this company does")
    business_story: str = Field(description="2-3 sentence business model explanation")
    investment_case: str = Field(description="Why this company might be interesting to study")
    key_monitorables: list[str] = Field(description="What to watch in coming quarters")
    quality_score: int = Field(ge=0, le=10)
    valuation_score: int = Field(ge=0, le=10)
    risk_score: int = Field(ge=0, le=10)
    overall_verdict: str = Field(description="Balanced 2-3 sentence overall verdict")
    agent_type: str = "summary"
    model_used: str
    generated_at: str


class AnalysisRequest(BaseModel):
    """Request body for triggering a fresh AI analysis."""
    agent_type: str = Field(
        description="Which agent to run: research | financial | quality | valuation | risk | summary"
    )
    force_refresh: bool = False
    period_year: int | None = None
    period_quarter: int | None = None
