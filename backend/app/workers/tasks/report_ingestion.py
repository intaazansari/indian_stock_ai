"""Placeholder for report ingestion task."""
from __future__ import annotations

import asyncio
import structlog
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.workers.tasks.report_ingestion.ingest_annual_report",
    queue="default",
)
def ingest_annual_report(company_id: str, year: int, pdf_url: str) -> None:
    """
    Download, parse, chunk, and embed an annual report PDF into Qdrant.

    Steps:
      1. Download PDF from BSE filings URL
      2. Extract text with pdfplumber
      3. Chunk text into sections
      4. Embed each chunk via OpenAI embeddings
      5. Upsert into Qdrant annual_reports collection
      6. Mark company's annual report as ingested
    """
    logger.info("report_ingestion.started", company_id=company_id, year=year)
    asyncio.run(_ingest(company_id, year, pdf_url))
    logger.info("report_ingestion.completed", company_id=company_id, year=year)


async def _ingest(company_id: str, year: int, pdf_url: str) -> None:
    # TODO: Implement PDF download, parsing, chunking, embedding, Qdrant upsert
    pass
