"""Management Quality Agent — evaluates promoter quality, capital allocation, governance."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.base_agent import BaseAgent
from app.core.config import settings


class ManagementState(TypedDict):
    company_id: str
    company_data: dict[str, Any]
    financial_context: dict[str, Any]
    management_context: dict[str, Any]
    result: dict[str, Any]


class ManagementAgent(BaseAgent):
    agent_name = "management"
    model_name = settings.OPENAI_ANALYSIS_MODEL

    def _build_graph(self) -> Any:
        graph = StateGraph(ManagementState)
        graph.add_node("build_context", self._build_context)
        graph.add_node("analyze", self._analyze)
        graph.set_entry_point("build_context")
        graph.add_edge("build_context", "analyze")
        graph.add_edge("analyze", END)
        return graph.compile()

    async def analyze(self, input_data: dict[str, Any]) -> dict[str, Any]:
        state = ManagementState(
            company_id=input_data["company_id"],
            company_data=input_data.get("company_data", {}),
            financial_context=input_data.get("financial_context", {}),
            management_context={},
            result={},
        )
        final_state = await self._graph.ainvoke(state)
        return final_state["result"]

    async def _build_context(self, state: ManagementState) -> ManagementState:
        cd  = state.get("company_data", {})
        fc  = state.get("financial_context", {})

        def _v(key: str, fallback: str = "N/A") -> Any:
            val = cd.get(key) or fc.get(key)
            return val if val not in (None, "", "N/A") else fallback

        # Capex track record from cash flow context
        capex   = fc.get("capex_cr", "N/A")
        fcf     = fc.get("fcf_cr", "N/A")
        cfo     = fc.get("cfo_cr", "N/A")
        capex_text = (
            f"Capex ₹{capex} Cr | FCF ₹{fcf} Cr | CFO ₹{cfo} Cr"
            if capex != "N/A" else "N/A"
        )

        state["management_context"] = {
            "company_name":              _v("name"),
            "sector":                    _v("sector"),
            "promoter_holding_pct":      _v("promoter_holding"),
            "fii_holding_pct":           cd.get("fii_holding_pct", "N/A"),
            "dii_holding_pct":           cd.get("dii_holding_pct", "N/A"),
            "promoter_pledging_pct":     "N/A (not collected)",
            "promoter_holding_change_3yr": "N/A (not computed)",
            "md_salary_cr":              "N/A (not collected)",
            "dividend_payout_avg_pct":   fc.get("dividend_yield", "N/A"),
            "capex_track_record":        capex_text,
            "roce":                      _v("roce"),
            "roe":                       _v("roe"),
            "debt_equity":               _v("debt_equity"),
            "cfo_pat_ratio":             fc.get("cfo_pat_ratio", "N/A"),
            "revenue_cagr_3yr":          fc.get("revenue_cagr_3yr", "N/A"),
            "pat_cagr_3yr":              fc.get("pat_cagr_3yr", "N/A"),
            "audit_firm":                "N/A (not collected)",
            "related_party_transactions":"N/A (not collected)",
        }
        return state

    async def _analyze(self, state: ManagementState) -> ManagementState:
        ctx = state["management_context"]
        prompt = f"""Evaluate the management quality of {ctx['company_name']} ({ctx.get('sector', '')}):

Promoter Holding: {ctx['promoter_holding_pct']}% | FII: {ctx['fii_holding_pct']}% | DII: {ctx['dii_holding_pct']}%
Promoter Pledged: {ctx['promoter_pledging_pct']} | 3-Year Change: {ctx['promoter_holding_change_3yr']}
ROCE: {ctx['roce']}% | ROE: {ctx['roe']}% | D/E: {ctx['debt_equity']}
CFO/PAT Ratio: {ctx['cfo_pat_ratio']} | Revenue CAGR (3yr): {ctx['revenue_cagr_3yr']}%
CapEx & Cash Flow: {ctx['capex_track_record']}
Dividend Yield: {ctx['dividend_payout_avg_pct']}%
Audit Firm: {ctx['audit_firm']} | RPT: {ctx['related_party_transactions']}

Return JSON:
{{
    "overall_score": <integer 0-10>,
    "capital_allocation_quality": "<assessment>",
    "promoter_commitment": "<assessment>",
    "governance_quality": "<assessment>",
    "key_positives": ["<positive>"],
    "concerns": ["<concern if any>"],
    "summary": "<2-3 sentence verdict on management>"
}}"""

        response = await self.llm.ainvoke([
            SystemMessage(content="You are a corporate governance expert evaluating Indian company management. Return pure JSON."),
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
            result_data = {"summary": response.content}
        state["result"] = {
            **result_data, "company_id": state["company_id"],
            "agent_type": "management", "model_used": self.model_name,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        return state
