"""
Risk Agent — detects red flags and evaluates business risks.

This is one of the most critical agents on the platform.
The Red Flag Detector is a key differentiator — no competitor does this well.

Categories:
  1. Accounting Red Flags   — receivables spike, inventory bloat, audit qualifications
  2. Governance Red Flags   — promoter pledging, related party transactions
  3. Financial Red Flags    — debt surge, FCF vs PAT divergence
  4. Business Red Flags     — revenue concentration, customer churn signals
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

SYSTEM_PROMPT = """You are a forensic financial analyst specializing in detecting accounting
fraud, governance issues, and business deterioration in Indian public companies.

Your responsibility is to look for RED FLAGS — warning signs that investors should be aware of.
Be specific. Reference the actual numbers. Do not cry wolf on minor issues.

Classify each risk as: low | medium | high | critical

Return pure JSON. No markdown."""

RISK_PROMPT_TEMPLATE = """Analyse the risk profile of this Indian company:

Company: {company_name}
Sector: {sector}

Financial Signals (Last 3 Years):
- Revenue Growth YoY: {revenue_growth}%
- PAT Growth YoY: {pat_growth}%
- Receivables Change YoY: {receivables_change}%
- Inventory Change YoY: {inventory_change}%
- CFO vs PAT ratio: {cfo_pat_ratio}
- Debt Growth YoY: {debt_growth}%
- Promoter Pledging: {promoter_pledged}%
- Interest Coverage: {interest_coverage}x
- Audit Qualifications: {audit_qualifications}

Return this exact JSON:
{{
    "overall_risk_level": "low|medium|high|critical",
    "red_flags": [
        {{
            "title": "<flag title>",
            "description": "<specific description with numbers>",
            "severity": "low|medium|high|critical",
            "category": "accounting|governance|business|financial"
        }}
    ],
    "business_risks": ["<risk 1>", "<risk 2>"],
    "financial_risks": ["<risk 1>", "<risk 2>"],
    "governance_risks": ["<risk 1>"],
    "regulatory_risks": ["<risk 1>"]
}}"""


class RiskState(TypedDict, total=False):
    company_id: str
    company_data: dict[str, Any]
    risk_context: dict[str, Any]
    result: dict[str, Any]


class RiskAgent(BaseAgent):
    agent_name = "risk"
    model_name = settings.OPENAI_ANALYSIS_MODEL

    def _build_graph(self) -> Any:
        graph = StateGraph(RiskState)
        graph.add_node("build_context", self._build_context)
        graph.add_node("detect_risks", self._detect_risks)
        graph.set_entry_point("build_context")
        graph.add_edge("build_context", "detect_risks")
        graph.add_edge("detect_risks", END)
        return graph.compile()

    async def analyze(self, input_data: dict[str, Any]) -> dict[str, Any]:
        state: RiskState = {
            "company_id": input_data["company_id"],
            "company_data": input_data.get("company_data", {}),
            # Use financial_context as the seed for risk_context
            "risk_context": input_data.get("financial_context", {}),
            "result": {},
        }
        final_state = await self._graph.ainvoke(state)
        return final_state["result"]

    async def _build_context(self, state: RiskState) -> RiskState:
        fc = state.get("risk_context", {})
        cd = state.get("company_data", {})

        def _v(key: str, fallback: str = "N/A") -> str:
            return str(fc.get(key) or fallback)

        state["risk_context"] = {
            "company_name":       _v("company_name") or cd.get("name", "Unknown"),
            "sector":             _v("sector") or cd.get("sector", "Unknown"),
            "revenue_growth":     _v("revenue_growth"),
            "pat_growth":         _v("pat_growth"),
            "receivables_change": _v("receivables_change"),
            "inventory_change":   "N/A",   # Not in current schema
            "cfo_pat_ratio":      _v("cfo_pat_ratio"),
            "debt_growth":        "N/A",   # Would need 2-year debt delta
            "promoter_pledged":   _v("promoter_pledged"),
            "interest_coverage":  _v("interest_coverage"),
            "audit_qualifications": "None reported",
        }
        return state

    async def _detect_risks(self, state: RiskState) -> RiskState:
        ctx = state["risk_context"]
        prompt = RISK_PROMPT_TEMPLATE.format(**ctx)

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
            result_data = {"raw_response": response.content, "overall_risk_level": "medium"}

        state["result"] = {
            **result_data,
            "company_id": state["company_id"],
            "agent_type": "risk",
            "model_used": self.model_name,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        return state
