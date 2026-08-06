"""
Financial data parser.

Transforms raw NSE/BSE API responses into normalised dicts
that can be directly inserted into the database via repositories.

Indian financial data is messy:
  - Values are sometimes in crores, sometimes in lakhs, sometimes in actual
  - Field names vary across data sources
  - Some quarters have restatements

This parser handles all normalisation in one place.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any


def parse_value_to_cr(value: Any, unit: str = "cr") -> Decimal | None:
    """
    Convert a financial value to crores (₹ Cr).

    NSE API returns values in different units depending on the field.
    Always normalise to crores for storage.
    """
    if value is None:
        return None
    try:
        v = Decimal(str(value).replace(",", "").strip())
        if unit == "lakhs":
            return v / 100
        if unit == "millions":
            return v / 10
        if unit == "thousands":
            return v / 100000
        return v  # already in crores
    except Exception:
        return None


def parse_income_statement(raw: dict[str, Any], symbol: str, year: int, quarter: int | None) -> dict[str, Any]:
    """
    Parse raw NSE/BSE income statement response into DB-ready dict.

    TODO: Map actual NSE API field names to our schema fields.
          NSE API field names change periodically — handle gracefully.
    """
    return {
        "period_type": "quarterly" if quarter else "annual",
        "period_year": year,
        "period_quarter": quarter,
        "revenue_cr": parse_value_to_cr(raw.get("revenue") or raw.get("totalRevenue")),
        "ebitda_cr": parse_value_to_cr(raw.get("ebitda")),
        "pat_cr": parse_value_to_cr(raw.get("pat") or raw.get("netProfit")),
        "eps_basic": parse_value_to_cr(raw.get("eps") or raw.get("basicEPS")),
        "total_expenses_cr": parse_value_to_cr(raw.get("totalExpenses")),
        "interest_cr": parse_value_to_cr(raw.get("financeCharges") or raw.get("interest")),
        "depreciation_cr": parse_value_to_cr(raw.get("depreciationAmortization")),
        "tax_cr": parse_value_to_cr(raw.get("tax") or raw.get("taxProvision")),
    }


def parse_balance_sheet(raw: dict[str, Any], year: int) -> dict[str, Any]:
    """Parse raw balance sheet response."""
    return {
        "period_type": "annual",
        "period_year": year,
        "period_quarter": None,
        "total_assets_cr": parse_value_to_cr(raw.get("totalAssets")),
        "shareholders_equity_cr": parse_value_to_cr(raw.get("shareholdersEquity") or raw.get("equity")),
        "long_term_debt_cr": parse_value_to_cr(raw.get("longTermBorrowings")),
        "short_term_debt_cr": parse_value_to_cr(raw.get("shortTermBorrowings")),
        "cash_cr": parse_value_to_cr(raw.get("cashAndCashEquivalents")),
        "receivables_cr": parse_value_to_cr(raw.get("tradeReceivables")),
        "inventories_cr": parse_value_to_cr(raw.get("inventories")),
    }
