"""
Analysis orchestration service.

Responsibilities:
  1. Check cache first (Redis fast cache → PostgreSQL analysis_cache).
  2. If cache miss or force_refresh, delegate to the appropriate AI agent.
  3. Store result in cache.
  4. Support streaming for real-time analysis.

This service is the bridge between the API layer and the AI agent layer.
"""
from __future__ import annotations

import json
import statistics
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import redis.asyncio as aioredis
import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analysis_cache import AnalysisCache
from app.schemas.analysis import (
    AnalysisRequest,
    ExecutiveSummaryResponse,
    FinancialAnalysisResponse,
    QualityScoreResponse,
    RiskAnalysisResponse,
    ValuationAnalysisResponse,
)

logger = structlog.get_logger(__name__)

AGENT_CACHE_KEY_PREFIX = "analysis_cache"


class AnalysisService:
    def __init__(self, session: AsyncSession, redis: aioredis.Redis | None) -> None:
        self.session = session
        self.redis = redis

    async def get_analysis(
        self,
        company_id: uuid.UUID,
        agent_type: str,
        force_refresh: bool = False,
    ) -> dict:
        """
        Return cached analysis or trigger a fresh run.

        Cache hierarchy:
          1. Redis (fast, TTL-based)
          2. PostgreSQL analysis_cache (persistent)
          3. AI agent (expensive, only if both caches miss)
        """
        redis_key = self._redis_key(company_id, agent_type)

        if not force_refresh:
            # 1. Try Redis fast cache (non-fatal if Redis is unavailable)
            if self.redis is not None:
                try:
                    cached = await self.redis.get(redis_key)
                    if cached:
                        logger.debug("analysis.cache.redis_hit", company_id=str(company_id), agent=agent_type)
                        return json.loads(cached)
                except Exception as exc:
                    logger.warning("analysis.cache.redis_unavailable", error=str(exc))

            # 2. Try PostgreSQL cache
            db_result = await self._get_from_db_cache(company_id, agent_type)
            if db_result and not db_result.is_stale:
                result_dict = db_result.analysis_json
                if self.redis is not None:
                    try:
                        await self.redis.setex(redis_key, settings.AI_ANALYSIS_CACHE_TTL, json.dumps(result_dict))
                    except Exception:
                        pass
                logger.debug("analysis.cache.db_hit", company_id=str(company_id), agent=agent_type)
                return result_dict

        # No cache — don't run the agent on a GET request (too expensive).
        # The frontend should use the POST /stream endpoint to trigger fresh analysis.
        raise HTTPException(status_code=404, detail="No cached analysis found. Use the stream endpoint to generate.")

        return result

    async def stream_analysis(
        self,
        company_id: uuid.UUID,
        agent_type: str,
    ) -> AsyncIterator[str]:
        """
        Run AI analysis, save to cache, and stream the result as SSE.
        Yields a single data event with the full result, then [DONE].
        """
        from app.agents.supervisor.supervisor_agent import SupervisorAgent
        from app.models.company import Company as CompanyModel
        from sqlalchemy import select as sa_select

        # Fetch real company context so agents can build meaningful prompts
        company_row = (await self.session.execute(
            sa_select(CompanyModel).where(CompanyModel.id == company_id)
        )).scalar_one_or_none()

        company_data: dict = {}
        if company_row:
            company_data = {
                "name": company_row.name or "",
                "sector": company_row.sector or "",
                "industry": company_row.industry or "",
                "description": company_row.description or f"{company_row.name} is a listed Indian company.",
                "market_cap_cr": str(company_row.market_cap_cr or ""),
                "cmp": str(company_row.cmp or ""),
                "promoter_holding_pct": str(company_row.promoter_holding_pct or ""),
                "nse_symbol": company_row.nse_symbol or "",
            }

        # Fetch real financial context from DB tables
        financial_context = await self._build_financial_context(company_id, company_data)

        agent = SupervisorAgent()
        result = await agent.analyze({
            "company_id": str(company_id),
            "agent_type": agent_type,
            "company_data": company_data,
            "financial_context": financial_context,
        })

        # Persist to DB — commit explicitly before streaming so GET requests
        # can find the result immediately after the first SSE event is received.
        await self._store_in_db_cache(company_id, agent_type, result)
        await self.session.commit()
        if self.redis is not None:
            try:
                redis_key = self._redis_key(company_id, agent_type)
                await self.redis.setex(redis_key, settings.AI_ANALYSIS_CACHE_TTL, json.dumps(result))
            except Exception:
                pass

        yield f"data: {json.dumps({'result': result})}\n\n"
        yield "data: [DONE]\n\n"

    async def _build_financial_context(
        self, company_id: uuid.UUID, company_data: dict
    ) -> dict:
        """
        Fetch the last 3 years of KeyRatios + latest BalanceSheet + CashFlow
        and return a flat dict the AI agents can embed directly into their prompts.
        """
        from app.models.financials import KeyRatio, BalanceSheet, CashFlow, IncomeStatement
        from sqlalchemy import select as sa_select, desc

        def _f(val, decimals: int = 2) -> str:
            """Format a Decimal/None as a rounded string, or 'N/A'."""
            if val is None:
                return "N/A"
            try:
                return str(round(float(val), decimals))
            except Exception:
                return "N/A"

        # ── Key Ratios: last 3 annual rows ────────────────────────────────────
        ratios_rows = (await self.session.execute(
            sa_select(KeyRatio)
            .where(KeyRatio.company_id == company_id, KeyRatio.period_type == "annual")
            .order_by(desc(KeyRatio.period_year))
            .limit(3)
        )).scalars().all()

        def _avg(rows, attr: str) -> str:
            vals = [float(getattr(r, attr)) for r in rows if getattr(r, attr) is not None]
            return str(round(sum(vals) / len(vals), 2)) if vals else "N/A"

        latest_r = ratios_rows[0] if ratios_rows else None

        # ── Latest Balance Sheet ──────────────────────────────────────────────
        bs = (await self.session.execute(
            sa_select(BalanceSheet)
            .where(BalanceSheet.company_id == company_id, BalanceSheet.period_type == "annual")
            .order_by(desc(BalanceSheet.period_year))
            .limit(1)
        )).scalar_one_or_none()

        # ── Latest Cash Flow ──────────────────────────────────────────────────
        cf = (await self.session.execute(
            sa_select(CashFlow)
            .where(CashFlow.company_id == company_id, CashFlow.period_type == "annual")
            .order_by(desc(CashFlow.period_year))
            .limit(1)
        )).scalar_one_or_none()

        # ── Last 3 Income Statements for revenue/PAT trend ────────────────────
        pl_rows = (await self.session.execute(
            sa_select(IncomeStatement)
            .where(IncomeStatement.company_id == company_id, IncomeStatement.period_type == "annual")
            .order_by(desc(IncomeStatement.period_year))
            .limit(3)
        )).scalars().all()

        latest_pl = pl_rows[0] if pl_rows else None

        # ── Compute receivables change YoY as a proxy for quality ─────────────
        bs_rows = (await self.session.execute(
            sa_select(BalanceSheet)
            .where(BalanceSheet.company_id == company_id, BalanceSheet.period_type == "annual")
            .order_by(desc(BalanceSheet.period_year))
            .limit(2)
        )).scalars().all()
        rec_change = "N/A"
        if len(bs_rows) == 2 and bs_rows[1].receivables_cr and bs_rows[1].receivables_cr != 0:
            delta = float(bs_rows[0].receivables_cr or 0) - float(bs_rows[1].receivables_cr)
            rec_change = str(round(delta / float(bs_rows[1].receivables_cr) * 100, 1))

        total_debt = "N/A"
        if bs:
            lt = float(bs.long_term_debt_cr or 0)
            st = float(bs.short_term_debt_cr or 0)
            total_debt = str(round(lt + st, 2))

        # CFO/PAT ratio — quality of earnings
        cfo_pat = "N/A"
        if cf and cf.cfo_cr and latest_pl and latest_pl.pat_cr and float(latest_pl.pat_cr) != 0:
            cfo_pat = str(round(float(cf.cfo_cr) / float(latest_pl.pat_cr), 2))

        # ── Historical Median P/E (from this company's own annual ratios) ─────────
        hist_pe_list = [
            float(r.pe_ratio)
            for r in ratios_rows
            if r.pe_ratio is not None and float(r.pe_ratio) > 0
        ]
        historical_pe_median_val = (
            round(statistics.median(hist_pe_list), 1) if len(hist_pe_list) >= 2 else None
        )

        # ── Sector Median P/E (latest annual PE across all companies in same sector) ─
        from app.models.company import Company as CompanyModel
        from sqlalchemy import func as sa_func

        sector_median_pe_val = None
        sector = company_data.get("sector", "")
        if sector and sector not in ("Unknown", "N/A", ""):
            try:
                latest_yr_subq = (
                    sa_select(
                        KeyRatio.company_id,
                        sa_func.max(KeyRatio.period_year).label("max_year"),
                    )
                    .where(KeyRatio.period_type == "annual")
                    .group_by(KeyRatio.company_id)
                    .subquery()
                )
                sector_pe_raw = (
                    await self.session.execute(
                        sa_select(KeyRatio.pe_ratio)
                        .join(
                            latest_yr_subq,
                            (KeyRatio.company_id == latest_yr_subq.c.company_id)
                            & (KeyRatio.period_year == latest_yr_subq.c.max_year),
                        )
                        .join(CompanyModel, CompanyModel.id == KeyRatio.company_id)
                        .where(
                            CompanyModel.sector == sector,
                            KeyRatio.period_type == "annual",
                            KeyRatio.pe_ratio.isnot(None),
                            KeyRatio.pe_ratio > 0,
                            KeyRatio.pe_ratio < 200,
                        )
                    )
                ).scalars().all()
                pe_floats = [float(v) for v in sector_pe_raw if v]
                if pe_floats:
                    sector_median_pe_val = round(statistics.median(pe_floats), 1)
            except Exception:
                pass  # Non-fatal — sector PE is best-effort

        return {
            # Company basics (repeated here for agent convenience)
            "company_name":     company_data.get("name", "Unknown"),
            "sector":           company_data.get("sector", "Unknown"),
            "industry":         company_data.get("industry", "Unknown"),
            "market_cap_cr":    company_data.get("market_cap_cr", "N/A"),
            "cmp":              company_data.get("cmp", "N/A"),
            "promoter_holding": company_data.get("promoter_holding_pct", "N/A"),
            # Valuation ratios
            "pe_ratio":         _f(getattr(latest_r, "pe_ratio", None)) if latest_r else "N/A",
            "pb_ratio":         _f(getattr(latest_r, "pb_ratio", None)) if latest_r else "N/A",
            "ev_ebitda":        _f(getattr(latest_r, "ev_ebitda", None)) if latest_r else "N/A",
            "ps_ratio":         _f(getattr(latest_r, "ps_ratio", None)) if latest_r else "N/A",
            "dividend_yield":   _f(getattr(latest_r, "dividend_yield_pct", None)) if latest_r else "N/A",
            # Profitability
            "roce":             _f(getattr(latest_r, "roce_pct", None)) if latest_r else "N/A",
            "roe":              _f(getattr(latest_r, "roe_pct", None)) if latest_r else "N/A",
            "roa":              _f(getattr(latest_r, "roa_pct", None)) if latest_r else "N/A",
            "npm":              _f(getattr(latest_r, "net_profit_margin_pct", None)) if latest_r else "N/A",
            "ebitda_margin":    _f(getattr(latest_r, "ebitda_margin_pct", None)) if latest_r else "N/A",
            "roce_avg":         _avg(ratios_rows, "roce_pct"),
            "roe_avg":          _avg(ratios_rows, "roe_pct"),
            "npm_avg":          _avg(ratios_rows, "net_profit_margin_pct"),
            # Growth
            "revenue_growth":   _f(getattr(latest_r, "revenue_growth_pct", None)) if latest_r else "N/A",
            "pat_growth":       _f(getattr(latest_r, "pat_growth_pct", None)) if latest_r else "N/A",
            "eps_growth":       _f(getattr(latest_r, "eps_growth_pct", None)) if latest_r else "N/A",
            "revenue_growth_avg": _avg(ratios_rows, "revenue_growth_pct"),
            # Health
            "debt_equity":      _f(getattr(latest_r, "debt_equity_ratio", None)) if latest_r else "N/A",
            "current_ratio":    _f(getattr(latest_r, "current_ratio", None)) if latest_r else "N/A",
            "interest_coverage": _f(getattr(latest_r, "interest_coverage", None)) if latest_r else "N/A",
            # Balance Sheet
            "total_debt_cr":    total_debt,
            "cash_cr":          _f(getattr(bs, "cash_cr", None)) if bs else "N/A",
            "shareholders_equity_cr": _f(getattr(bs, "shareholders_equity_cr", None)) if bs else "N/A",
            # Cash Flow
            "fcf_cr":           _f(getattr(cf, "free_cash_flow_cr", None)) if cf else "N/A",
            "cfo_cr":           _f(getattr(cf, "cfo_cr", None)) if cf else "N/A",
            "cfo_pat_ratio":    cfo_pat,
            # P&L snapshot
            "revenue_cr":       _f(getattr(latest_pl, "revenue_cr", None)) if latest_pl else "N/A",
            "pat_cr":           _f(getattr(latest_pl, "pat_cr", None)) if latest_pl else "N/A",
            "ebitda_cr":        _f(getattr(latest_pl, "ebitda_cr", None)) if latest_pl else "N/A",
            # Forensics
            "receivables_change": rec_change,
            "promoter_pledged": "N/A",  # Not in current DB schema — placeholder
            # Sector / Historical PE (numeric, not strings)
            "sector_median_pe_val":    sector_median_pe_val,
            "historical_pe_median_val": historical_pe_median_val,
        }

    async def _run_agent(self, company_id: uuid.UUID, agent_type: str) -> dict:
        """Dispatch to the correct agent based on agent_type."""
        from app.agents.supervisor.supervisor_agent import SupervisorAgent
        agent = SupervisorAgent()
        result = await agent.analyze(
            {"company_id": str(company_id), "agent_type": agent_type}
        )
        return result

    async def _get_from_db_cache(
        self, company_id: uuid.UUID, agent_type: str
    ) -> AnalysisCache | None:
        result = await self.session.execute(
            select(AnalysisCache)
            .where(
                AnalysisCache.company_id == company_id,
                AnalysisCache.agent_type == agent_type,
            )
            .order_by(AnalysisCache.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _store_in_db_cache(
        self, company_id: uuid.UUID, agent_type: str, result: dict
    ) -> None:
        existing = await self._get_from_db_cache(company_id, agent_type)
        now_str = datetime.now(tz=timezone.utc).isoformat()

        if existing:
            existing.analysis_json = result
            existing.is_stale = False
            existing.model_used = result.get("model_used", settings.OPENAI_ANALYSIS_MODEL)
            self.session.add(existing)
        else:
            cache_entry = AnalysisCache(
                company_id=company_id,
                agent_type=agent_type,
                analysis_json=result,
                model_used=result.get("model_used", settings.OPENAI_ANALYSIS_MODEL),
                prompt_version="1.0.0",
                is_stale=False,
            )
            self.session.add(cache_entry)

        await self.session.flush()

    def _redis_key(self, company_id: uuid.UUID, agent_type: str) -> str:
        return f"{AGENT_CACHE_KEY_PREFIX}:{company_id}:{agent_type}"
