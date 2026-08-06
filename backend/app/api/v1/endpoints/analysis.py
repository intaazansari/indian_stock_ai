"""
AI Analysis endpoints.

Two modes:
  1. GET  /{symbol}/analysis/{agent_type}  — returns cached analysis (fast)
  2. POST /{symbol}/analysis/stream        — streams fresh analysis via SSE

Design principles:
  - Cache-first: Never run AI on every request.
  - Stream for UX: When user explicitly requests fresh analysis, stream tokens.
  - Rate limit: AI endpoints have stricter per-user hourly limits.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.dependencies import (
    AIRateLimitDep,
    CurrentUserID,
    DBSession,
    OptionalUserID,
    RedisClient,
)
from app.schemas.analysis import AnalysisRequest
from app.services.analysis_service import AnalysisService
from app.services.company_service import CompanyService

router = APIRouter()

AgentType = Literal[
    "research", "financial", "quality", "valuation",
    "risk", "management", "quarterly", "summary"
]


@router.get("/{symbol}/analysis/{agent_type}")
async def get_cached_analysis(
    symbol: str,
    agent_type: AgentType,
    db: DBSession,
    redis: RedisClient,
) -> dict:
    """
    Return pre-computed AI analysis for a company.

    Cache hierarchy: Redis (fast) → PostgreSQL → AI agent (if no cache).
    This endpoint is safe to call on every page load.
    """
    company_service = CompanyService(db)
    company = await company_service.get_by_symbol(symbol.upper())

    analysis_service = AnalysisService(db, redis)
    return await analysis_service.get_analysis(
        company_id=company.id,
        agent_type=agent_type,
    )


@router.post("/{symbol}/analysis/stream")
async def stream_fresh_analysis(
    symbol: str,
    payload: AnalysisRequest,
    db: DBSession,
    redis: RedisClient,
    user_id: OptionalUserID,
    _rate_limit: None = AIRateLimitDep,
) -> StreamingResponse:
    """
    Stream fresh AI analysis via Server-Sent Events (SSE).

    This endpoint:
      - Requires authentication
      - Is rate-limited (20 requests/hour per user)
      - Bypasses cache and runs a fresh AI analysis
      - Streams tokens back to the client in real-time

    Client should use EventSource or fetch with streaming.
    """
    company_service = CompanyService(db)
    company = await company_service.get_by_symbol(symbol.upper())

    analysis_service = AnalysisService(db, redis)

    return StreamingResponse(
        analysis_service.stream_analysis(
            company_id=company.id,
            agent_type=payload.agent_type,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable nginx buffering for SSE
        },
    )
