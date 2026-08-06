"""
Executive Summary Agent — synthesises all agents into an investor brief.

This is the FIRST thing an investor sees on the company page.
It must be: concise, accurate, opinionated (but fair), and actionable.

Input: Results from Research, Financial, Quality, Valuation, Risk agents.
Output: A 5-part executive summary with scores and key takeaways.
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

SYSTEM_PROMPT = """You are the head of equity research at a top-tier Indian investment fund.

Your job is to write an Executive Summary for a company that a busy portfolio manager
can read in 60 seconds and decide whether the company deserves deeper study.

Be direct. Be specific. No fluff. No generic statements.
Write like you are briefing a senior analyst, not writing a school essay.

Return pure JSON."""

SUMMARY_PROMPT_TEMPLATE = """Create an Executive Summary for this company:

Company: {company_name}
Sector: {sector}
Market Cap: ₹{market_cap_cr} Cr
Current PE: {pe_ratio}x

Business: {business_description}
Quality Score: {quality_score}/10
Financial Health: {financial_health}
Key Risks: {key_risks}
Valuation Commentary: {valuation_commentary}

Return this exact JSON:
{{
    "one_liner": "<Single sentence: what does this company do? Be specific.>",
    "business_story": "<2-3 sentences about the business model and competitive position>",
    "investment_case": "<Why might this company be worth studying? What's the bull case?>",
    "key_monitorables": [
        "<What should investors track in the next 2 quarters?>",
        "<Second monitorable>",
        "<Third monitorable>"
    ],
    "quality_score": <integer 0-10>,
    "valuation_score": <integer 0-10>,
    "risk_score": <integer 0-10, where 10 = lowest risk>,
    "overall_verdict": "<Balanced 2-3 sentence verdict. End with: Worthy of further research? Yes/No/Maybe.>"
}}"""


class SummaryState(TypedDict, total=False):
    company_id: str
    aggregated_context: dict[str, Any]
    result: dict[str, Any]


class ExecutiveSummaryAgent(BaseAgent):
    agent_name = "summary"
    model_name = settings.OPENAI_ANALYSIS_MODEL

    def _build_graph(self) -> Any:
        graph = StateGraph(SummaryState)
        graph.add_node("aggregate_context", self._aggregate_context)
        graph.add_node("generate_summary", self._generate_summary)
        graph.set_entry_point("aggregate_context")
        graph.add_edge("aggregate_context", "generate_summary")
        graph.add_edge("generate_summary", END)
        return graph.compile()

    async def analyze(self, input_data: dict[str, Any]) -> dict[str, Any]:
        state: SummaryState = {
            "company_id": input_data["company_id"],
            "aggregated_context": input_data.get("aggregated_context", {}),
            "result": {},
        }
        final_state = await self._graph.ainvoke(state)
        return final_state["result"]

    async def _aggregate_context(self, state: SummaryState) -> SummaryState:
        # Use real company data if injected by the service layer
        company = state.get("aggregated_context", {})
        if not company.get("company_name"):
            # Build from raw company_data if passed, else use generic placeholders
            # (injected via aggregated_context from supervisor/service)
            company = {
                "company_name": "Unknown Company",
                "sector": "Unknown Sector",
                "market_cap_cr": "N/A",
                "pe_ratio": "N/A",
                "business_description": "An Indian listed company.",
                "quality_score": "N/A",
                "financial_health": "Data not available",
                "key_risks": "Data not available",
                "valuation_commentary": "Data not available",
            }
        state["aggregated_context"] = company
        return state

    async def _generate_summary(self, state: SummaryState) -> SummaryState:
        ctx = state["aggregated_context"]
        prompt = SUMMARY_PROMPT_TEMPLATE.format(**ctx)

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
            result_data = {"raw_response": response.content}

        state["result"] = {
            **result_data,
            "company_id": state["company_id"],
            "agent_type": "summary",
            "model_used": self.model_name,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        return state
