from __future__ import annotations

# Import all models here so Alembic autogenerate detects them
from app.models.user import User
from app.models.company import Company
from app.models.financials import IncomeStatement, BalanceSheet, CashFlow, KeyRatio
from app.models.analysis_cache import AnalysisCache
from app.models.watchlist import Watchlist, Portfolio

__all__ = [
    "User",
    "Company",
    "IncomeStatement",
    "BalanceSheet",
    "CashFlow",
    "KeyRatio",
    "AnalysisCache",
    "Watchlist",
    "Portfolio",
]
