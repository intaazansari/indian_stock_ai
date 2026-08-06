"""
Background AI analysis tasks.

These tasks run in the Celery ai_analysis queue.
They pre-compute AI analysis and store results in the analysis_cache table
so users get instant page loads instead of waiting for AI to run.

Triggered by:
  - New quarterly results published (via data_sync tasks)
  - Manual refresh request from admin
  - Periodic stale cache refresh
"""
from __future__ import annotations

import asyncio
import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.workers.tasks.ai_analysis.run_company_analysis",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="ai_analysis",
)
def run_company_analysis(
    self,
    company_id: str,
    agent_type: str,
    force_refresh: bool = True,
) -> dict:
    """
    Run AI analysis for a specific company and agent type.
    Results are stored in the analysis_cache table.
    """
    logger.info(
        "ai_analysis.task.started",
        company_id=company_id,
        agent_type=agent_type,
    )
    try:
        result = asyncio.run(_run_analysis(company_id, agent_type))
        logger.info("ai_analysis.task.completed", company_id=company_id, agent_type=agent_type)
        return result
    except Exception as exc:
        logger.error("ai_analysis.task.failed", company_id=company_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.tasks.ai_analysis.refresh_stale_analysis_cache",
    queue="ai_analysis",
)
def refresh_stale_analysis_cache() -> None:
    """
    Find all stale analysis cache entries and refresh them.
    Runs every 6 hours via Celery Beat.
    """
    logger.info("ai_analysis.refresh_stale.started")
    asyncio.run(_refresh_stale())
    logger.info("ai_analysis.refresh_stale.completed")


async def _run_analysis(company_id: str, agent_type: str) -> dict:
    """Async implementation — run AI agent and store result."""
    from app.agents.supervisor.supervisor_agent import SupervisorAgent
    agent = SupervisorAgent()
    return await agent.analyze({"company_id": company_id, "agent_type": agent_type})


async def _refresh_stale() -> None:
    """Find stale cache entries and queue individual refresh tasks."""
    # TODO: Query analysis_cache for is_stale=True entries
    # and dispatch run_company_analysis tasks for each
    pass
