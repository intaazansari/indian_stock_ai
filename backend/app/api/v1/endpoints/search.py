from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import DBSession
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.company import CompanySearchResult
from app.services.company_service import CompanyService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CompanySearchResult])
async def search_companies(
    db: DBSession,
    q: str = Query(min_length=1, max_length=100, description="Company name, NSE symbol, or BSE code"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
) -> PaginatedResponse[CompanySearchResult]:
    """
    Search for companies by name, NSE symbol, or BSE code.

    Used by the global search bar. Ordered by market cap (largest first).
    """
    service = CompanyService(db)
    params = PaginationParams(page=page, page_size=page_size)
    return await service.search(query=q, params=params)
