"""
Research Agent — understands and explains the business.

Responsibility: Generate a clear, plain-English explanation of:
  - What the company does
  - How it makes money
  - What its competitive moat is
  - Key business risks and opportunities

This agent powers the "Business Story" card on the company page.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agents.base_agent import BaseAgent
from app.core.config import settings

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are an experienced equity research analyst specializing in Indian public companies.

Your task is to explain a company's business in plain English — the kind of explanation
a fund manager would give to a new analyst in their first meeting.

Be concise, accurate, and insightful. Avoid jargon. Avoid generic statements.
Every sentence must be specific to this company.

Return your analysis as a structured JSON object."""

ANALYSIS_PROMPT_TEMPLATE = """Analyze the following Indian company and provide a business overview:

Company: {company_name}
Sector: {sector}
Industry: {industry}
Description: {description}

Provide your analysis as a JSON object with these exact keys:
{{
    "one_liner": "Single sentence: what does this company do?",
    "business_model": "2-3 sentences explaining how the company makes money",
    "competitive_moat": "What structural advantage does this company have?",
    "key_customers": "Who are the primary customers?",
    "key_risks": ["risk 1", "risk 2", "risk 3"],
    "growth_drivers": ["driver 1", "driver 2"],
    "sector_tailwinds": "Is the sector growing? Why?"
}}"""


class ResearchState(TypedDict, total=False):
    company_id: str
    company_data: dict[str, Any]
    financial_context: dict[str, Any]
    result: dict[str, Any]


class ResearchAgent(BaseAgent):
    agent_name = "research"
    model_name = settings.OPENAI_SUMMARY_MODEL  # Cheaper model sufficient for research

    def _build_graph(self) -> Any:
        graph = StateGraph(ResearchState)
        graph.add_node("fetch_company_data", self._fetch_company_data)
        graph.add_node("analyze", self._analyze)
        graph.set_entry_point("fetch_company_data")
        graph.add_edge("fetch_company_data", "analyze")
        graph.add_edge("analyze", END)
        return graph.compile()

    async def analyze(self, input_data: dict[str, Any]) -> dict[str, Any]:
        state: ResearchState = {
            "company_id": input_data["company_id"],
            "company_data": input_data.get("company_data", {}),
            "financial_context": input_data.get("financial_context", {}),
            "result": {},
        }
        final_state = await self._graph.ainvoke(state)
        return final_state["result"]

    async def _fetch_company_data(self, state: ResearchState) -> ResearchState:
        """Use injected company context if available, else fall back to placeholder."""
        injected = state.get("company_data", {})
        if injected.get("name"):
            # Real data was passed in from AnalysisService
            state["company_data"] = injected
        else:
            state["company_data"] = {
                "name": "Unknown Company",
                "sector": "Unknown Sector",
                "industry": "Unknown Industry",
                "description": "An Indian listed company.",
            }
        return state

    async def _analyze(self, state: ResearchState) -> ResearchState:
        company = state["company_data"]
        fc = state.get("financial_context", {})

        # Include key financial stats so the AI can make the business overview richer
        financial_context_str = ""
        if fc.get("revenue_cr") and fc["revenue_cr"] != "N/A":
            financial_context_str = f"""

Key Financials (for context, do not repeat these numbers verbatim):
  Revenue: ₹{fc.get('revenue_cr','N/A')} Cr | PAT: ₹{fc.get('pat_cr','N/A')} Cr
  Market Cap: ₹{fc.get('market_cap_cr','N/A')} Cr | ROCE: {fc.get('roce','N/A')}%
  Revenue Growth: {fc.get('revenue_growth','N/A')}% YoY | Promoter Holding: {fc.get('promoter_holding','N/A')}%"""

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            company_name=company.get("name", ""),
            sector=company.get("sector", ""),
            industry=company.get("industry", ""),
            description=company.get("description", ""),
        ) + financial_context_str

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = await self.llm.ainvoke(messages)
        self._log_token_usage(response, {"company_id": state["company_id"]})

        import json
        try:
            content = response.content
            # Strip markdown code fences if present
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
            "agent_type": "research",
            "model_used": self.model_name,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        return state
