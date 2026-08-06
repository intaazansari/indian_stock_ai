"""
Supervisor Agent — routes analysis requests to the appropriate sub-agent.

Uses LangGraph to implement a supervisor pattern:
  - Accepts an input with company_id + agent_type
  - Routes to the correct specialized agent
  - Returns the agent's structured output

This is intentionally simple for MVP. As we scale, the supervisor
can implement multi-agent coordination, parallel execution, and
result synthesis.
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

import structlog
from langgraph.graph import END, StateGraph

from app.agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

AgentType = Literal[
    "research",
    "financial",
    "quality",
    "valuation",
    "risk",
    "management",
    "quarterly",
    "summary",
]


class SupervisorState(TypedDict, total=False):
    company_id: str
    agent_type: str
    company_data: dict[str, Any]
    financial_context: dict[str, Any]
    result: dict[str, Any]
    error: str | None


class SupervisorAgent(BaseAgent):
    """
    Supervisor agent that routes to specialized sub-agents.

    For MVP: single-agent routing.
    For v2: parallel multi-agent coordination with result synthesis.
    """
    agent_name = "supervisor"

    def _build_graph(self) -> Any:
        graph = StateGraph(SupervisorState)

        graph.add_node("route", self._route_node)
        graph.add_node("run_research", self._run_research)
        graph.add_node("run_financial", self._run_financial)
        graph.add_node("run_quality", self._run_quality)
        graph.add_node("run_valuation", self._run_valuation)
        graph.add_node("run_risk", self._run_risk)
        graph.add_node("run_management", self._run_management)
        graph.add_node("run_quarterly", self._run_quarterly)
        graph.add_node("run_summary", self._run_summary)

        graph.set_entry_point("route")

        graph.add_conditional_edges(
            "route",
            self._router,
            {
                "research": "run_research",
                "financial": "run_financial",
                "quality": "run_quality",
                "valuation": "run_valuation",
                "risk": "run_risk",
                "management": "run_management",
                "quarterly": "run_quarterly",
                "summary": "run_summary",
            },
        )

        for node in ["run_research", "run_financial", "run_quality", "run_valuation",
                     "run_risk", "run_management", "run_quarterly", "run_summary"]:
            graph.add_edge(node, END)

        return graph.compile()

    async def analyze(self, input_data: dict[str, Any]) -> dict[str, Any]:
        state: SupervisorState = {
            "company_id": input_data["company_id"],
            "agent_type": input_data["agent_type"],
            "company_data": input_data.get("company_data", {}),
            "financial_context": input_data.get("financial_context", {}),
            "result": {},
            "error": None,
        }
        final_state = await self._graph.ainvoke(state)
        if final_state.get("error"):
            raise RuntimeError(f"Agent error: {final_state['error']}")
        return final_state["result"]

    # ── Router ────────────────────────────────────────────────────────────────

    async def _route_node(self, state: SupervisorState) -> SupervisorState:
        logger.info(
            "supervisor.routing",
            company_id=state["company_id"],
            agent_type=state["agent_type"],
        )
        return state

    def _router(self, state: SupervisorState) -> str:
        return state["agent_type"]

    # ── Agent runner nodes ────────────────────────────────────────────────────

    def _agent_input(self, state: SupervisorState) -> dict[str, Any]:
        """Build the common input dict forwarded to every sub-agent."""
        return {
            "company_id": state["company_id"],
            "company_data": state.get("company_data", {}),
            "financial_context": state.get("financial_context", {}),
        }

    async def _run_research(self, state: SupervisorState) -> SupervisorState:
        from app.agents.research.research_agent import ResearchAgent
        result = await ResearchAgent().analyze(self._agent_input(state))
        return {**state, "result": result}

    async def _run_financial(self, state: SupervisorState) -> SupervisorState:
        from app.agents.financial_analysis.financial_agent import FinancialAnalysisAgent
        result = await FinancialAnalysisAgent().analyze(self._agent_input(state))
        return {**state, "result": result}

    async def _run_quality(self, state: SupervisorState) -> SupervisorState:
        from app.agents.business_quality.quality_agent import BusinessQualityAgent
        result = await BusinessQualityAgent().analyze(self._agent_input(state))
        return {**state, "result": result}

    async def _run_valuation(self, state: SupervisorState) -> SupervisorState:
        from app.agents.valuation.valuation_agent import ValuationAgent
        result = await ValuationAgent().analyze(self._agent_input(state))
        return {**state, "result": result}

    async def _run_risk(self, state: SupervisorState) -> SupervisorState:
        from app.agents.risk.risk_agent import RiskAgent
        result = await RiskAgent().analyze(self._agent_input(state))
        return {**state, "result": result}

    async def _run_management(self, state: SupervisorState) -> SupervisorState:
        from app.agents.management.management_agent import ManagementAgent
        result = await ManagementAgent().analyze(self._agent_input(state))
        return {**state, "result": result}

    async def _run_quarterly(self, state: SupervisorState) -> SupervisorState:
        from app.agents.quarterly_results.quarterly_agent import QuarterlyResultsAgent
        result = await QuarterlyResultsAgent().analyze(self._agent_input(state))
        return {**state, "result": result}

    async def _run_summary(self, state: SupervisorState) -> SupervisorState:
        from app.agents.executive_summary.summary_agent import ExecutiveSummaryAgent
        fc = state.get("financial_context", {})
        cd = state.get("company_data", {})
        inp = self._agent_input(state)
        inp["aggregated_context"] = {
            "company_name": cd.get("name") or fc.get("company_name", "Unknown"),
            "sector":       cd.get("sector") or fc.get("sector", "Unknown"),
            "market_cap_cr": fc.get("market_cap_cr") or cd.get("market_cap_cr", "N/A"),
            "pe_ratio":     fc.get("pe_ratio", "N/A"),
            "business_description": cd.get("description", ""),
            "quality_score": "See quality tab",
            "financial_health": (
                f"ROCE {fc.get('roce','N/A')}%, ROE {fc.get('roe','N/A')}%, "
                f"D/E {fc.get('debt_equity','N/A')}, Interest Coverage {fc.get('interest_coverage','N/A')}x"
            ),
            "key_risks": "See risk tab",
            "valuation_commentary": (
                f"PE {fc.get('pe_ratio','N/A')}x, PB {fc.get('pb_ratio','N/A')}x, "
                f"EV/EBITDA {fc.get('ev_ebitda','N/A')}x"
            ),
        }
        result = await ExecutiveSummaryAgent().analyze(inp)
        return {**state, "result": result}
