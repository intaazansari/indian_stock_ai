"""Financial Analysis Agent — P&L trends, balance sheet health, cash flow quality."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.base_agent import BaseAgent
from app.core.config import settings

SYSTEM_PROMPT = """You are a senior financial analyst specialising in Indian public company financials.
Analyse the provided financial data and identify key trends, strengths, and weaknesses.
Be specific. Reference actual numbers. Return pure JSON."""

FINANCIAL_PROMPT_TEMPLATE = """Analyse the financials of {company_name}:

10-Year Revenue CAGR: {revenue_cagr}%
10-Year PAT CAGR: {pat_cagr}%
Average EBITDA Margin: {avg_ebitda_margin}%
Average Net Profit Margin: {avg_npm}%
Average CFO/PAT: {avg_cfo_pat}
Average Debt/Equity: {avg_de}
10-Year ROCE Average: {avg_roce}%

Return JSON:
{{
    "revenue_trend": "<Revenue growth story>",
    "profitability_trend": "<Margin trend and direction>",
    "balance_sheet_health": "<Debt, equity, liquidity assessment>",
    "cash_flow_quality": "<CFO vs PAT quality assessment>",
    "key_insights": [
        {{"title": "<insight>", "insight": "<detail>", "sentiment": "positive|neutral|negative", "metric_value": "<value>"}}
    ],
    "red_flags": ["<flag if any>"],
    "positives": ["<positive 1>", "<positive 2>"]
}}"""


class FinancialState(TypedDict, total=False):
    company_id: str
    company_data: dict[str, Any]
    financial_context: dict[str, Any]
    result: dict[str, Any]


class FinancialAnalysisAgent(BaseAgent):
    agent_name = "financial"
    model_name = settings.OPENAI_ANALYSIS_MODEL

    def _build_graph(self) -> Any:
        graph = StateGraph(FinancialState)
        graph.add_node("build_context", self._build_context)
        graph.add_node("analyze", self._analyze)
        graph.set_entry_point("build_context")
        graph.add_edge("build_context", "analyze")
        graph.add_edge("analyze", END)
        return graph.compile()

    async def analyze(self, input_data: dict[str, Any]) -> dict[str, Any]:
        state: FinancialState = {
            "company_id": input_data["company_id"],
            "company_data": input_data.get("company_data", {}),
            "financial_context": input_data.get("financial_context", {}),
            "result": {},
        }
        final_state = await self._graph.ainvoke(state)
        return final_state["result"]

    async def _build_context(self, state: FinancialState) -> FinancialState:
        fc = state.get("financial_context", {})
        cd = state.get("company_data", {})

        def _v(key: str, fallback: str = "N/A") -> str:
            return str(fc.get(key) or fallback)

        state["financial_context"] = {
            "company_name":      _v("company_name") or cd.get("name", "Unknown"),
            "revenue_cagr":      _v("revenue_growth_avg"),
            "pat_cagr":          _v("pat_growth"),
            "avg_ebitda_margin": _v("ebitda_margin"),
            "avg_npm":           _v("npm_avg"),
            "avg_cfo_pat":       _v("cfo_pat_ratio"),
            "avg_de":            _v("debt_equity"),
            "avg_roce":          _v("roce_avg"),
        }
        return state

    async def _analyze(self, state: FinancialState) -> FinancialState:
        prompt = FINANCIAL_PROMPT_TEMPLATE.format(**state["financial_context"])
        response = await self.llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        self._log_token_usage(response, {"company_id": state["company_id"]})
        try:
            content = response.content
            if "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                if content.startswith("json"):
                    content = content[4:].strip()
            result_data = json.loads(content)
        except (json.JSONDecodeError, IndexError):
            result_data = {"raw_response": response.content}
        state["result"] = {
            **result_data, "company_id": state["company_id"],
            "agent_type": "financial", "model_used": self.model_name,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        return state
