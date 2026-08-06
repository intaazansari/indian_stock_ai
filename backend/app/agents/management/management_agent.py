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
            management_context=input_data.get("management_context", {}),
            result={},
        )
        final_state = await self._graph.ainvoke(state)
        return final_state["result"]

    async def _build_context(self, state: ManagementState) -> ManagementState:
        # TODO: Fetch promoter data, salary data, capital allocation history from DB
        state["management_context"] = {
            "company_name": "Company Name",
            "promoter_holding_pct": 68.5,
            "promoter_pledging_pct": 0.0,
            "promoter_holding_change_3yr": -1.2,
            "md_salary_cr": 5.2,
            "dividend_payout_avg_pct": 35.0,
            "buyback_history": "None in last 5 years",
            "capex_track_record": "Disciplined, returns-focused",
            "audit_firm": "Big 4",
            "related_party_transactions": "Low, well-disclosed",
        }
        return state

    async def _analyze(self, state: ManagementState) -> ManagementState:
        ctx = state["management_context"]
        prompt = f"""Evaluate the management quality of {ctx['company_name']}:

Promoter Holding: {ctx['promoter_holding_pct']}% | Pledged: {ctx['promoter_pledging_pct']}% | Change (3Y): {ctx['promoter_holding_change_3yr']}%
MD Salary: ₹{ctx['md_salary_cr']} Cr | Dividend Payout (avg): {ctx['dividend_payout_avg_pct']}%
Buyback: {ctx['buyback_history']}
CapEx Track Record: {ctx['capex_track_record']}
Audit Firm: {ctx['audit_firm']}
Related Party Transactions: {ctx['related_party_transactions']}

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
