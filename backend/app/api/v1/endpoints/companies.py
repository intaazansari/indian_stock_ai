from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import DBSession, OptionalUserID
from app.schemas.common import PaginationParams
from app.schemas.company import CompanyDetail, CompanySearchResult, PeerCompanyItem
from app.schemas.common import PaginatedResponse
from app.services.company_service import CompanyService

router = APIRouter()


@router.get("/{symbol}", response_model=CompanyDetail)
async def get_company(symbol: str, db: DBSession) -> CompanyDetail:
    """
    Get full company profile by NSE symbol or BSE code.

    This is the entry point to the company page.
    Returns complete company metadata including promoter holding,
    sector classification, and market data.
    """
    service = CompanyService(db)
    company = await service.get_by_symbol(symbol.upper())
    return CompanyDetail.model_validate(company)


@router.get("/{symbol}/peers", response_model=list[PeerCompanyItem])
async def get_peers(symbol: str, db: DBSession) -> list[PeerCompanyItem]:
    """
    Get peer companies for comparison.

    Peers are companies in the same industry, ordered by market cap.
    """
    service = CompanyService(db)
    return await service.get_peers(symbol.upper())
