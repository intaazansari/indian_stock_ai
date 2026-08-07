from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, companies, financials, analysis, search, screener, watchlist, portfolio, market

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(companies.router, prefix="/companies", tags=["Companies"])
api_v1_router.include_router(financials.router, prefix="/companies", tags=["Financials"])
api_v1_router.include_router(analysis.router, prefix="/companies", tags=["AI Analysis"])
api_v1_router.include_router(search.router, prefix="/search", tags=["Search"])
api_v1_router.include_router(screener.router, prefix="/screener", tags=["Screener"])
api_v1_router.include_router(watchlist.router, prefix="/watchlist", tags=["Watchlist"])
api_v1_router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
api_v1_router.include_router(market.router, prefix="/market", tags=["Market"])
