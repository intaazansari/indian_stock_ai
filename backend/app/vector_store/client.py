"""
Qdrant vector store client.

Collections:
  - annual_reports       → Chunked annual report text for RAG
  - company_news         → News articles with sentiment metadata
  - earnings_transcripts → Earnings call transcripts

Used by:
  - AnnualReportAgent    → RAG-powered deep dive
  - NewsSentimentAgent   → News context retrieval
  - ResearchAgent        → Background research retrieval
"""
from __future__ import annotations

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from app.core.config import settings

logger = structlog.get_logger(__name__)

_client: AsyncQdrantClient | None = None

VECTOR_SIZE = 1536  # text-embedding-3-small output dimension


async def get_qdrant_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )
        logger.info("qdrant.connected", url=settings.QDRANT_URL)
    return _client


async def ensure_collections() -> None:
    """Create Qdrant collections if they do not exist. Called on startup."""
    client = await get_qdrant_client()

    collections_config = [
        (settings.QDRANT_COLLECTION_ANNUAL_REPORTS, {"company_id": "keyword", "year": "integer", "section": "keyword"}),
        (settings.QDRANT_COLLECTION_NEWS, {"company_id": "keyword", "sentiment": "keyword", "source": "keyword"}),
        (settings.QDRANT_COLLECTION_TRANSCRIPTS, {"company_id": "keyword", "year": "integer", "quarter": "integer"}),
    ]

    existing = {c.name for c in (await client.get_collections()).collections}

    for collection_name, _ in collections_config:
        if collection_name not in existing:
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info("qdrant.collection.created", name=collection_name)
