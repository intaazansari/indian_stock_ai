from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Query

from app.core.dependencies import DBSession
from app.schemas.financials import FinancialSummary
from app.services.financial_service import FinancialService
from app.services.company_service import CompanyService

router = APIRouter()


@router.get("/{symbol}/financials", response_model=FinancialSummary)
async def get_financials(
    symbol: str,
    db: DBSession,
    period_type: Literal["annual", "quarterly"] = Query(default="annual"),
    years: int = Query(default=10, ge=1, le=20),
) -> FinancialSummary:
    """
    Get complete financial statements for a company.

    Returns P&L, Balance Sheet, Cash Flow, and Key Ratios
    for the specified period (annual or quarterly) and number of years.
    """
    company_service = CompanyService(db)
    company = await company_service.get_by_symbol(symbol.upper())

    financial_service = FinancialService(db)
    return await financial_service.get_financial_summary(
        company_id=company.id,
        period_type=period_type,
        years=years,
    )
