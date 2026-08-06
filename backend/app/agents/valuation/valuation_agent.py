"""Valuation Agent — PE, PB, EV/EBITDA analysis with fair value commentary."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.base_agent import BaseAgent
from app.core.config import settings


class ValuationState(TypedDict, total=False):
    company_id: str
    company_data: dict[str, Any]
    valuation_context: dict[str, Any]
    result: dict[str, Any]


class ValuationAgent(BaseAgent):
    agent_name = "valuation"
    model_name = settings.OPENAI_ANALYSIS_MODEL

    def _build_graph(self) -> Any:
        graph = StateGraph(ValuationState)
        graph.add_node("build_context", self._build_context)
        graph.add_node("analyze", self._analyze)
        graph.set_entry_point("build_context")
        graph.add_edge("build_context", "analyze")
        graph.add_edge("analyze", END)
        return graph.compile()

    async def analyze(self, input_data: dict[str, Any]) -> dict[str, Any]:
        state: ValuationState = {
            "company_id": input_data["company_id"],
            "company_data": input_data.get("company_data", {}),
            "valuation_context": input_data.get("financial_context", {}),
            "result": {},
        }
        final_state = await self._graph.ainvoke(state)
        return final_state["result"]

    async def _build_context(self, state: ValuationState) -> ValuationState:
        # financial_context is already populated by AnalysisService via input_data
        fc = state.get("valuation_context", {})
        cd = state.get("company_data", {})

        def _v(key: str, fallback: str = "N/A") -> str:
            return fc.get(key) or cd.get(key) or fallback

        state["valuation_context"] = {
            "company_name":            _v("company_name") or cd.get("name", "Unknown"),
            "sector":                  _v("sector"),
            "market_cap_cr":           _v("market_cap_cr"),
            "cmp":                     _v("cmp"),
            "current_pe":              _v("pe_ratio"),
            "current_pb":              _v("pb_ratio"),
            "ev_ebitda":               _v("ev_ebitda"),
            "ps_ratio":                _v("ps_ratio"),
            "dividend_yield":          _v("dividend_yield"),
            "roce":                    _v("roce"),
            "roe":                     _v("roe"),
            "revenue_growth_latest":   _v("revenue_growth"),
            "revenue_growth_3yr_avg":  _v("revenue_growth_avg"),
            "pat_growth":              _v("pat_growth"),
            "ebitda_margin":           _v("ebitda_margin"),
            "npm":                     _v("npm"),
            "debt_equity":             _v("debt_equity"),
            "interest_coverage":       _v("interest_coverage"),
            "fcf_cr":                  _v("fcf_cr"),
            # Sector / historical comparison — raw numeric values (float | None)
            "sector_median_pe":        fc.get("sector_median_pe_val"),
            "historical_pe_median":    fc.get("historical_pe_median_val"),
        }
        return state

    async def _analyze(self, state: ValuationState) -> ValuationState:
        ctx = state["valuation_context"]
        prompt = f"""Analyse the valuation of {ctx['company_name']} (Sector: {ctx['sector']}):

VALUATION MULTIPLES
  Current PE:          {ctx['current_pe']}x
  Current PB:          {ctx['current_pb']}x
  EV/EBITDA:           {ctx['ev_ebitda']}x
  Price/Sales:         {ctx['ps_ratio']}x
  Dividend Yield:      {ctx['dividend_yield']}%
  Market Cap:          ₹{ctx['market_cap_cr']} Cr

QUALITY & GROWTH
  ROCE:                {ctx['roce']}%
  ROE:                 {ctx['roe']}%
  Revenue Growth YoY:  {ctx['revenue_growth_latest']}%
  Revenue Growth 3Y:   {ctx['revenue_growth_3yr_avg']}% avg
  PAT Growth YoY:      {ctx['pat_growth']}%
  EBITDA Margin:       {ctx['ebitda_margin']}%
  Net Profit Margin:   {ctx['npm']}%

BALANCE SHEET
  Debt/Equity:         {ctx['debt_equity']}x
  Interest Coverage:   {ctx['interest_coverage']}x
  Free Cash Flow:      ₹{ctx['fcf_cr']} Cr

SECTOR & HISTORICAL CONTEXT
  Sector Median P/E:     {ctx.get('sector_median_pe', 'N/A')}x  (median PE of peers in same sector)
  Historical Median P/E: {ctx.get('historical_pe_median', 'N/A')}x  (this company's own 3-year median PE)

Based on THESE ACTUAL NUMBERS for {ctx['company_name']}, provide a valuation assessment.
Do not use generic sector averages — use the data provided.

Return JSON:
{{
    "valuation_commentary": "<2-3 sentence assessment specific to these numbers>",
    "is_overvalued": true/false/null,
    "fair_value_estimate": <number or null — CMP-based estimate>,
    "upside_downside_pct": <number or null>,
    "valuation_methodology": "<PE/PB/DCF basis used>",
    "key_assumptions": ["<assumption 1>", "<assumption 2>"]
}}"""

        response = await self.llm.ainvoke([
            SystemMessage(content="You are a senior equity analyst. Assess valuations for Indian public companies. Return pure JSON."),
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
            result_data = {"valuation_commentary": response.content}
        state["result"] = {
            **result_data, "company_id": state["company_id"],
            "current_pe": ctx.get("current_pe"),
            "current_pb": ctx.get("current_pb"),
            "sector_median_pe":    ctx.get("sector_median_pe"),
            "historical_pe_median": ctx.get("historical_pe_median"),
            "agent_type": "valuation", "model_used": self.model_name,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        return state
