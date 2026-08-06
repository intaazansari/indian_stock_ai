"""
Business Quality Agent — scores the business across 5 dimensions.

Responsibility:
  Produce a Quality Score Card with scores (0-10) and explanations for:
  1. Business Quality     — moat, pricing power, competitive position
  2. Financial Health     — balance sheet strength, debt, liquidity
  3. Management Quality   — promoter track record, capital allocation
  4. Growth Quality       — revenue consistency, margin trajectory
  5. Valuation            — relative to quality and history

This is the core differentiator of the platform.
Investors see a 5-dimension scorecard with plain-English explanations
instead of a table of numbers.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TypedDict

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.base_agent import BaseAgent
from app.core.config import settings

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are a seasoned equity research analyst with 20 years of experience
analysing Indian public companies.

Your task is to evaluate the quality of a business on five dimensions.
Be objective. Be specific. Back your scores with evidence from the financial data.

Score each dimension from 0 to 10:
  0-3: Poor
  4-5: Average
  6-7: Good
  8-9: Excellent
  10:  Exceptional (rare)

Return a structured JSON object. No markdown. Pure JSON."""

QUALITY_PROMPT_TEMPLATE = """Evaluate this Indian company:

Company: {company_name}
Sector: {sector}
Market Cap: ₹{market_cap_cr} Cr

Key Financials (Last 3 Years):
- Revenue Growth (CAGR): {revenue_growth}%
- ROCE (avg): {roce}%
- ROE (avg): {roe}%
- Net Profit Margin (avg): {npm}%
- Debt/Equity: {de_ratio}
- Promoter Holding: {promoter_holding}%
- Free Cash Flow (last year): ₹{fcf_cr} Cr

Return this exact JSON structure:
{{
    "overall_score": <integer 0-10>,
    "business_quality": {{
        "label": "Business Quality",
        "score": <integer 0-10>,
        "explanation": "<specific explanation based on the data>"
    }},
    "financial_health": {{
        "label": "Financial Health",
        "score": <integer 0-10>,
        "explanation": "<specific explanation>"
    }},
    "management_quality": {{
        "label": "Management Quality",
        "score": <integer 0-10>,
        "explanation": "<specific explanation>"
    }},
    "growth_quality": {{
        "label": "Growth Quality",
        "score": <integer 0-10>,
        "explanation": "<specific explanation>"
    }},
    "valuation": {{
        "label": "Valuation",
        "score": <integer 0-10>,
        "explanation": "<specific explanation>"
    }},
    "summary": "<2-3 sentence overall verdict>",
    "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>"]
}}"""


class QualityState(TypedDict, total=False):
    company_id: str
    financial_context: dict[str, Any]
    company_data: dict[str, Any]
    result: dict[str, Any]


class BusinessQualityAgent(BaseAgent):
    agent_name = "quality"
    model_name = settings.OPENAI_ANALYSIS_MODEL

    def _build_graph(self) -> Any:
        graph = StateGraph(QualityState)
        graph.add_node("build_context", self._build_context)
        graph.add_node("score", self._score)
        graph.set_entry_point("build_context")
        graph.add_edge("build_context", "score")
        graph.add_edge("score", END)
        return graph.compile()

    async def analyze(self, input_data: dict[str, Any]) -> dict[str, Any]:
        state: QualityState = {
            "company_id": input_data["company_id"],
            "company_data": input_data.get("company_data", {}),
            "financial_context": input_data.get("financial_context", {}),
            "result": {},
        }
        final_state = await self._graph.ainvoke(state)
        return final_state["result"]

    async def _build_context(self, state: QualityState) -> QualityState:
        fc = state.get("financial_context", {})
        cd = state.get("company_data", {})

        def _v(key: str, fallback: str = "N/A") -> str:
            return str(fc.get(key) or fallback)

        state["financial_context"] = {
            "company_name":    _v("company_name") or cd.get("name", "Unknown"),
            "sector":          _v("sector") or cd.get("sector", "Unknown"),
            "market_cap_cr":   _v("market_cap_cr") or cd.get("market_cap_cr", "N/A"),
            "revenue_growth":  _v("revenue_growth_avg"),
            "roce":            _v("roce_avg"),
            "roe":             _v("roe_avg"),
            "npm":             _v("npm_avg"),
            "de_ratio":        _v("debt_equity"),
            "promoter_holding": _v("promoter_holding") or cd.get("promoter_holding_pct", "N/A"),
            "fcf_cr":          _v("fcf_cr"),
        }
        return state

    async def _score(self, state: QualityState) -> QualityState:
        ctx = state["financial_context"]
        prompt = QUALITY_PROMPT_TEMPLATE.format(**ctx)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = await self.llm.ainvoke(messages)
        self._log_token_usage(response, {"company_id": state["company_id"]})

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            result_data = json.loads(content)
        except (json.JSONDecodeError, IndexError):
            result_data = {"raw_response": response.content, "overall_score": 5}

        state["result"] = {
            **result_data,
            "company_id": state["company_id"],
            "agent_type": "quality",
            "model_used": self.model_name,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        return state
