"""Quarterly Results Agent — QoQ and YoY trend analysis for the latest quarter."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.base_agent import BaseAgent
from app.core.config import settings


class QuarterlyState(TypedDict):
    company_id: str
    company_data: dict[str, Any]
    financial_context: dict[str, Any]
    quarterly_context: dict[str, Any]
    result: dict[str, Any]


class QuarterlyResultsAgent(BaseAgent):
    agent_name = "quarterly"
    model_name = settings.OPENAI_SUMMARY_MODEL

    def _build_graph(self) -> Any:
        graph = StateGraph(QuarterlyState)
        graph.add_node("build_context", self._build_context)
        graph.add_node("analyze", self._analyze)
        graph.set_entry_point("build_context")
        graph.add_edge("build_context", "analyze")
        graph.add_edge("analyze", END)
        return graph.compile()

    async def analyze(self, input_data: dict[str, Any]) -> dict[str, Any]:
        state = QuarterlyState(
            company_id=input_data["company_id"],
            company_data=input_data.get("company_data", {}),
            financial_context=input_data.get("financial_context", {}),
            quarterly_context={},
            result={},
        )
        final_state = await self._graph.ainvoke(state)
        return final_state["result"]

    async def _build_context(self, state: QuarterlyState) -> QuarterlyState:
        cd  = state.get("company_data", {})
        fc  = state.get("financial_context", {})

        quarters = fc.get("quarterly_results", [])
        company_name = cd.get("name", fc.get("company_name", "Unknown"))

        ctx: dict[str, Any] = {"company_name": company_name}

        if len(quarters) >= 1:
            q0 = quarters[0]
            label0 = f"Q{q0.get('period_quarter','?')} FY{str(q0.get('period_year','?'))[-2:]}"
            ctx["latest_quarter"]      = label0
            ctx["revenue_cr"]          = q0.get("revenue_cr", "N/A")
            ctx["pat_cr"]              = q0.get("pat_cr", "N/A")
            ctx["ebitda_cr"]           = q0.get("ebitda_cr", "N/A")
            ctx["ebitda_margin"]       = q0.get("ebitda_margin", "N/A")
            ctx["eps_basic"]           = q0.get("eps_basic", "N/A")

        # QoQ comparison (Q0 vs Q1)
        def _pct_chg(cur, prev):
            try:
                c, p = float(cur), float(prev)
                if p == 0:
                    return "N/A"
                return round((c - p) / abs(p) * 100, 1)
            except (TypeError, ValueError):
                return "N/A"

        if len(quarters) >= 2:
            q1 = quarters[1]
            ctx["revenue_qoq"] = _pct_chg(ctx.get("revenue_cr"), q1.get("revenue_cr"))
            ctx["pat_qoq"]     = _pct_chg(ctx.get("pat_cr"), q1.get("pat_cr"))
            ctx["ebitda_margin_prev_q"] = q1.get("ebitda_margin", "N/A")
        else:
            ctx.setdefault("revenue_qoq", "N/A")
            ctx.setdefault("pat_qoq",     "N/A")
            ctx.setdefault("ebitda_margin_prev_q", "N/A")

        # YoY comparison (Q0 vs same quarter last year)
        if len(quarters) >= 5:
            q4 = quarters[4]
            ctx["revenue_yoy"] = _pct_chg(ctx.get("revenue_cr"), q4.get("revenue_cr"))
            ctx["pat_yoy"]     = _pct_chg(ctx.get("pat_cr"),     q4.get("pat_cr"))
        else:
            ctx.setdefault("revenue_yoy", "N/A")
            ctx.setdefault("pat_yoy",     "N/A")

        ctx.setdefault("latest_quarter", "Latest Quarter")
        ctx["management_commentary"] = "No recent commentary available."
        state["quarterly_context"] = ctx
        return state

    async def _analyze(self, state: QuarterlyState) -> QuarterlyState:
        ctx = state["quarterly_context"]
        prompt = f"""Analyse {ctx.get('latest_quarter', 'the latest quarter')} results for {ctx['company_name']}:

Revenue: ₹{ctx.get('revenue_cr', 'N/A')} Cr | Growth: {ctx.get('revenue_qoq', 'N/A')}% QoQ | {ctx.get('revenue_yoy', 'N/A')}% YoY
PAT: ₹{ctx.get('pat_cr', 'N/A')} Cr | Growth: {ctx.get('pat_qoq', 'N/A')}% QoQ | {ctx.get('pat_yoy', 'N/A')}% YoY
EBITDA Margin: {ctx.get('ebitda_margin', 'N/A')}% (prev Q: {ctx.get('ebitda_margin_prev_q', 'N/A')}%)
EPS (Basic): ₹{ctx.get('eps_basic', 'N/A')}

Return JSON:
{{
    "headline": "<One sentence: was this a good/bad quarter?>",
    "revenue_analysis": "<Revenue trend assessment>",
    "margin_analysis": "<Margin trend assessment>",
    "key_highlights": ["<highlight 1>", "<highlight 2>", "<highlight 3>"],
    "concerns": ["<concern if any>"],
    "what_changed": "<What changed vs last quarter — positive or negative?>",
    "outlook": "<What does management expect next quarter?>"
}}"""

        response = await self.llm.ainvoke([
            SystemMessage(content="You are an equity analyst covering Indian companies. Analyse quarterly results concisely. Return pure JSON."),
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
            result_data = {"headline": response.content}
        state["result"] = {
            **result_data, "company_id": state["company_id"],
            "agent_type": "quarterly", "model_used": self.model_name,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        return state
