"""
Abstract base class for all AI agents.

Architecture:
  - Every agent is a LangGraph StateGraph.
  - Agents have one responsibility and one output schema.
  - Agents support both batch (analyze) and streaming (stream) modes.
  - Token usage is tracked and logged for cost monitoring.

All agents must implement:
  - _build_graph()  → returns a compiled LangGraph graph
  - analyze()       → runs the graph and returns a typed dict
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

import structlog
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph

from app.core.config import settings

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """
    Base class for all AI agents.

    Subclasses define their own StateGraph, tools, prompts, and output schema.
    """

    #: Override in subclass to use a different model for this agent
    model_name: str = settings.OPENAI_ANALYSIS_MODEL
    agent_name: str = "base"

    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0,
            streaming=True,
            api_key=settings.OPENAI_API_KEY,
            # Supports any OpenAI-compatible endpoint: Groq, Azure, Ollama, etc.
            base_url=settings.OPENAI_BASE_URL or None,
        )
        self._graph = self._build_graph()

    @abstractmethod
    def _build_graph(self) -> Any:
        """Build and compile the LangGraph StateGraph for this agent."""
        ...

    @abstractmethod
    async def analyze(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Run the agent graph to completion and return a structured result.

        Args:
            input_data: Dict containing at minimum 'company_id' and agent-specific context.

        Returns:
            Structured dict matching the agent's output schema.
        """
        ...

    async def stream(self, input_data: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        """
        Stream agent output tokens.

        Yields partial output dicts as the agent processes.
        Default implementation runs the graph and yields the final result.
        Override for true token-level streaming.
        """
        logger.info(
            f"{self.agent_name}.stream.started",
            company_id=input_data.get("company_id"),
        )
        async for chunk in self._graph.astream(input_data):
            yield chunk

    def _log_token_usage(self, response: Any, context: dict[str, Any]) -> None:
        """Log token usage for cost monitoring."""
        usage = getattr(response, "usage_metadata", None)
        if usage:
            logger.info(
                f"{self.agent_name}.token_usage",
                input_tokens=usage.get("input_tokens"),
                output_tokens=usage.get("output_tokens"),
                **context,
            )
