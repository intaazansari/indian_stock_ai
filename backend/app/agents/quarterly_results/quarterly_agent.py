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
            quarterly_context=input_data.get("quarterly_context", {}),
            result={},
        )
        final_state = await self._graph.ainvoke(state)
        return final_state["result"]

    async def _build_context(self, state: QuarterlyState) -> QuarterlyState:
        # TODO: Fetch latest quarterly vs prior quarter and same quarter last year
        state["quarterly_context"] = {
            "company_name": "Company Name",
            "latest_quarter": "Q2 FY25",
            "revenue_qoq": 5.2, "revenue_yoy": 12.8,
            "pat_qoq": 8.1, "pat_yoy": 18.5,
            "ebitda_margin_current": 22.5, "ebitda_margin_prev_q": 21.0,
            "management_commentary": "Demand environment remains robust...",
        }
        return state

    async def _analyze(self, state: QuarterlyState) -> QuarterlyState:
        ctx = state["quarterly_context"]
        prompt = f"""Analyse Q2 FY25 results for {ctx['company_name']}:

Revenue Growth: {ctx['revenue_qoq']}% QoQ | {ctx['revenue_yoy']}% YoY
PAT Growth: {ctx['pat_qoq']}% QoQ | {ctx['pat_yoy']}% YoY
EBITDA Margin: {ctx['ebitda_margin_current']}% (prev Q: {ctx['ebitda_margin_prev_q']}%)
Management Commentary: {ctx['management_commentary']}

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
