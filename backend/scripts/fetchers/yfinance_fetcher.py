"""
Yahoo Finance data fetcher for Indian stocks.

Data sources used:
  - yfinance   → company info, 5-year annual financials (P&L, BS, CF)
  - NSE symbol with .NS suffix for NSE-listed stocks

Currency notes:
  - Most Indian companies report in INR; yfinance returns monetary values
    in INR (individual rupees) and we divide by CRORE (10,000,000) → ₹ Cr.
  - Some IT/export companies (Infosys, Wipro, HCL Tech, etc.) report
    financial statements in USD. yfinance signals this via
    ticker.info["financialCurrency"] = "USD".
    In this case all monetary values are multiplied by the live USD/INR rate
    AFTER the Cr conversion so that stored values are always in ₹ Crores.
    EPS (per-share) values are also converted INR per share.
  - Market cap from ticker.info["marketCap"] is always in the trading
    currency (INR for NSE) so no FX conversion is applied to it.

Limitations:
  - Promoter holding: yfinance 'heldPercentInsiders' is unreliable for India
    → left as None; Screener.in fetcher fills this
  - Face value: not available in yfinance → default to ₹1 (most Nifty50 stocks)
  - Some quarterly data may be missing for specific periods

Usage:
    fetcher = YFinanceFetcher()
    data = await fetcher.fetch_all("TCS")
    # data = {"company": {...}, "income_statements": [...], ...}
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd
import requests_cache
import structlog
import yfinance as yf

logger = structlog.get_logger(__name__)

CRORE = 10_000_000          # 1 crore = 10 million rupees
REQUEST_DELAY = 3.0         # seconds between API calls — increased to reduce 429s

# Install a disk-based HTTP cache for yfinance requests.
# Same ticker data within 1 hour is served from cache — no Yahoo Finance hit.
# Cache file: backend/yfinance_cache.sqlite
requests_cache.install_cache(
    "yfinance_cache",
    backend="sqlite",
    expire_after=3600,          # 1 hour
    allowable_codes=[200],
)


def _to_cr(value: Any) -> Decimal | None:
    """Convert an INR value to ₹ Crores. Returns None for missing/invalid data."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return Decimal(str(round(float(value) / CRORE, 2)))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _to_dec(value: Any, scale: int = 2) -> Decimal | None:
    """Convert a raw number to Decimal with given precision."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return Decimal(str(round(float(value), scale)))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _get(df: pd.DataFrame, *keys: str) -> Any:
    """
    Safely retrieve the first matching key from a DataFrame row.
    yfinance field names change occasionally; provide fallback names.
    """
    if df is None or df.empty:
        return None
    for key in keys:
        if key in df.index:
            return df.loc[key]
    return None


def _get_val(series: Any, col_idx: int = 0) -> Any:
    """Extract a scalar value from a pandas Series at a given column index."""
    if series is None:
        return None
    try:
        if isinstance(series, pd.Series):
            vals = series.dropna()
            if len(vals) > col_idx:
                return float(vals.iloc[col_idx])
        return float(series)
    except (TypeError, ValueError, IndexError):
        return None


def _fiscal_year(ts: pd.Timestamp) -> int:
    """
    Map a date to an Indian fiscal year.
    FY ends March 31 → March 31 2024 = FY2024.
    """
    if ts.month <= 3:
        return ts.year
    return ts.year + 1


def _fiscal_quarter(ts: pd.Timestamp) -> tuple[int, int]:
    """
    Map a date to an Indian (fiscal year, quarter).
    FY = Apr-Mar; Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar.

    Examples:
      2024-06-30 → (FY2025, Q1)
      2024-09-30 → (FY2025, Q2)
      2024-12-31 → (FY2025, Q3)
      2025-03-31 → (FY2025, Q4)
    """
    month = ts.month
    if month <= 3:
        q = 4
    elif month <= 6:
        q = 1
    elif month <= 9:
        q = 2
    else:
        q = 3
    return _fiscal_year(ts), q


# ── Currency conversion helpers ───────────────────────────────────────────────

# Some Indian companies (e.g. Infosys, Wipro, HCL Tech) report financial
# statements in USD on yfinance even though their NSE price is in INR.
# We detect this via ticker.info["financialCurrency"] and convert all
# monetary values by the USD/INR rate before storing them as ₹ Crores.

_usd_inr_rate_cache: float | None = None


def _get_usd_inr_rate() -> float:
    """Return the current USD/INR exchange rate with in-process caching."""
    global _usd_inr_rate_cache
    if _usd_inr_rate_cache is not None:
        return _usd_inr_rate_cache
    try:
        rate = float(yf.Ticker("USDINR=X").fast_info.last_price)
        if 70 < rate < 110:  # sanity check
            _usd_inr_rate_cache = rate
            logger.info("yfinance.usd_inr.fetched", rate=round(rate, 2))
            return rate
    except Exception:
        pass
    logger.warning("yfinance.usd_inr.fallback", rate=85.0)
    return 85.0


def _apply_currency_fx(rows: list[dict], fx: float) -> list[dict]:
    """
    Post-process financial rows: multiply all *_cr fields and per-share
    (eps_basic, eps_diluted, dividend_per_share) by *fx* to convert from
    foreign reporting currency (USD) to INR.

    Works for both annual and quarterly rows.
    Ratio/pct/growth fields are left untouched.
    """
    _per_share = {"eps_basic", "eps_diluted", "dividend_per_share"}
    result: list[dict] = []
    for row in rows:
        new_row: dict = {}
        for key, val in row.items():
            if val is None:
                new_row[key] = val
            elif key.endswith("_cr") or key in _per_share:
                try:
                    new_row[key] = Decimal(str(round(float(val) * fx, 2)))
                except (TypeError, ValueError, InvalidOperation):
                    new_row[key] = val
            else:
                new_row[key] = val
        result.append(new_row)
    return result


@dataclass
class FetchResult:
    """Container for all data fetched for one company."""
    nse_symbol: str
    company: dict[str, Any]
    income_statements: list[dict[str, Any]]
    balance_sheets: list[dict[str, Any]]
    cash_flows: list[dict[str, Any]]
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return bool(self.company.get("name"))


class YFinanceFetcher:
    """
    Fetches company data from Yahoo Finance for NSE-listed Indian stocks.

    Add `.NS` suffix for NSE; `.BO` suffix for BSE.
    NSE is preferred — better data coverage for Indian companies.
    """

    def __init__(self, delay: float = REQUEST_DELAY) -> None:
        self.delay = delay

    def fetch_all(self, nse_symbol: str, years: int = 5) -> FetchResult:
        """
        Fetch all data for one company synchronously.

        Args:
            nse_symbol: NSE symbol (e.g. 'TCS', 'RELIANCE')
            years: Number of annual periods to fetch

        Returns:
            FetchResult with all available data
        """
        ticker_symbol = f"{nse_symbol}.NS"
        logger.info("yfinance.fetch.start", symbol=ticker_symbol)

        result = FetchResult(
            nse_symbol=nse_symbol,
            company={},
            income_statements=[],
            balance_sheets=[],
            cash_flows=[],
        )

        try:
            ticker = yf.Ticker(ticker_symbol)

            # ── Company info ──────────────────────────────────────────────
            result.company = self._fetch_company_info(ticker, nse_symbol)

            # If 429 hit — info returns no name — skip financials entirely
            if not result.company.get("name") or result.company["name"] == nse_symbol:
                logger.warning("yfinance.rate_limited", symbol=ticker_symbol)
                result.errors.append("429: Yahoo Finance rate limit — retry in 15 min")
                return result

            time.sleep(self.delay)

            # ── Financial statements ──────────────────────────────────────
            result.income_statements = self._fetch_income_statements(ticker, years)
            time.sleep(self.delay)

            result.balance_sheets = self._fetch_balance_sheets(ticker, years)
            time.sleep(self.delay)

            result.cash_flows = self._fetch_cash_flows(ticker, years)
            time.sleep(self.delay)

            # ── Currency conversion (USD-reporting companies) ─────────────
            # Some companies (Infosys, Wipro, HCL Tech, etc.) report financial
            # statements in USD. Detect and convert all monetary values to INR.
            fin_currency = result.company.get("financial_currency", "INR")
            if fin_currency and fin_currency != "INR":
                fx = _get_usd_inr_rate()
                logger.info(
                    "yfinance.currency.converting",
                    symbol=ticker_symbol,
                    from_currency=fin_currency,
                    usd_inr=round(fx, 2),
                )
                result.income_statements = _apply_currency_fx(result.income_statements, fx)
                result.balance_sheets    = _apply_currency_fx(result.balance_sheets,    fx)
                result.cash_flows        = _apply_currency_fx(result.cash_flows,        fx)

            logger.info(
                "yfinance.fetch.complete",
                symbol=ticker_symbol,
                income_rows=len(result.income_statements),
                bs_rows=len(result.balance_sheets),
                cf_rows=len(result.cash_flows),
            )

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            result.errors.append(error_msg)
            logger.error("yfinance.fetch.failed", symbol=ticker_symbol, error=error_msg)

        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    def _fetch_company_info(self, ticker: yf.Ticker, nse_symbol: str) -> dict[str, Any]:
        info: dict = {}
        try:
            info = ticker.info or {}
        except Exception as e:
            logger.warning("yfinance.info.failed", symbol=nse_symbol, error=str(e))
            return {"name": nse_symbol, "nse_symbol": nse_symbol}

        market_cap_raw = info.get("marketCap")
        cmp_raw = info.get("currentPrice") or info.get("regularMarketPrice")

        return {
            "name": info.get("longName") or info.get("shortName") or nse_symbol,
            "nse_symbol": nse_symbol,
            "bse_code": None,               # filled by screener fetcher
            "isin": info.get("isin"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "description": (info.get("longBusinessSummary") or "")[:2000] or None,
            "website": info.get("website"),
            "market_cap_cr": _to_cr(market_cap_raw),
            "cmp": _to_dec(cmp_raw),
            "face_value": _to_dec(info.get("faceValue") or 1),
            # Promoter holding unreliable from yfinance for Indian co's
            # Screener.in fetcher will fill this
            "promoter_holding_pct": _to_dec(
                (info.get("heldPercentInsiders") or 0) * 100, scale=2
            ) or None,
            "employee_count": info.get("fullTimeEmployees"),
            "founded_year": None,
            "headquarters": info.get("city"),
            "week52_high": _to_dec(info.get("fiftyTwoWeekHigh")),
            "week52_low":  _to_dec(info.get("fiftyTwoWeekLow")),
            # financialCurrency may differ from trading currency (e.g. INFY.NS reports in USD)
            "financial_currency": info.get("financialCurrency", "INR"),
        }

    def _fetch_income_statements(
        self, ticker: yf.Ticker, years: int
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            # yfinance 0.2.x renamed .financials → .income_stmt
            fin = getattr(ticker, "income_stmt", None)
            if not isinstance(fin, pd.DataFrame) or fin.empty:
                fin = getattr(ticker, "financials", pd.DataFrame())
            if not isinstance(fin, pd.DataFrame) or fin.empty:
                return rows

            for col in list(fin.columns)[:years]:
                col_ts = pd.Timestamp(col)

                def gv(*keys: str) -> Any:
                    """Get value for this column from the first matching row key."""
                    for key in keys:
                        if key in fin.index:
                            val = fin.loc[key, col]
                            if pd.notna(val):
                                return float(val)
                    return None

                revenue_s     = gv("Total Revenue", "Operating Revenue")
                ebitda_s      = gv("EBITDA", "Normalized EBITDA")
                pat_s         = gv("Net Income", "Net Income Common Stockholders")
                dep_s         = gv("Reconciled Depreciation", "Depreciation And Amortization In Income Statement")
                ebit_s        = gv("EBIT", "Operating Income")
                interest_s    = gv("Interest Expense Non Operating", "Net Interest Income")
                tax_raw       = gv("Tax Provision")
                pbt_raw       = gv("Pretax Income")
                eps_basic_raw = gv("Basic EPS", "Basic Earnings Per Share")
                eps_dil_raw   = gv("Diluted EPS", "Diluted Earnings Per Share")
                total_exp_raw = gv("Total Expenses", "Operating Expense")

                revenue   = _to_cr(revenue_s)
                ebitda    = _to_cr(ebitda_s)
                pat       = _to_cr(pat_s)
                dep       = _to_cr(dep_s)
                ebit      = _to_cr(ebit_s)
                interest  = _to_cr(abs(interest_s) if interest_s else None)
                tax       = _to_cr(abs(tax_raw) if tax_raw else None)
                pbt       = _to_cr(pbt_raw)
                total_exp = _to_cr(total_exp_raw)

                # EPS is per share — already in INR, not in crores
                eps_basic   = _to_dec(eps_basic_raw)
                eps_diluted = _to_dec(eps_dil_raw)

                rows.append({
                    "period_type": "annual",
                    "period_year": _fiscal_year(col_ts),
                    "period_quarter": None,
                    "revenue_cr": revenue,
                    "ebitda_cr": ebitda,
                    "pat_cr": pat,
                    "depreciation_cr": dep,
                    "ebit_cr": ebit,
                    "interest_cr": interest,
                    "pbt_cr": pbt,
                    "tax_cr": tax,
                    "total_expenses_cr": total_exp,
                    "eps_basic": eps_basic,
                    "eps_diluted": eps_diluted,
                    "dividend_per_share": None,
                })
        except Exception as e:
            logger.warning("yfinance.income.failed", error=str(e))

        return rows

    def _fetch_balance_sheets(
        self, ticker: yf.Ticker, years: int
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            bs: pd.DataFrame = ticker.balance_sheet
            if bs is None or bs.empty:
                return rows

            for col in list(bs.columns)[:years]:
                col_ts = pd.Timestamp(col)

                def v(s, _col=col):
                    for key in s:
                        if key in bs.index:
                            val = bs.loc[key, _col]
                            if pd.notna(val):
                                return _to_cr(float(val))
                    return None

                rows.append({
                    "period_type": "annual",
                    "period_year": _fiscal_year(col_ts),
                    "period_quarter": None,
                    "total_assets_cr":         v(("Total Assets",)),
                    "fixed_assets_cr":          v(("Net PPE", "Net Property Plant Equipment")),
                    "current_assets_cr":        v(("Current Assets",)),
                    "cash_cr":                  v(("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")),
                    "inventories_cr":           v(("Inventory",)),
                    "receivables_cr":           v(("Receivables", "Accounts Receivable")),
                    "investments_cr":           v(("Investments And Advances", "Long Term Investments")),
                    "total_liabilities_cr":     v(("Total Liabilities Net Minority Interest", "Total Liabilities")),
                    "long_term_debt_cr":        v(("Long Term Debt", "Long Term Debt And Capital Lease Obligation")),
                    "short_term_debt_cr":       v(("Current Debt", "Current Debt And Capital Lease Obligation")),
                    "current_liabilities_cr":   v(("Current Liabilities",)),
                    "trade_payables_cr":        v(("Payables And Accrued Expenses", "Accounts Payable")),
                    "shareholders_equity_cr":   v(("Stockholders Equity", "Total Equity Gross Minority Interest")),
                    "share_capital_cr":         v(("Capital Stock", "Common Stock")),
                    "reserves_surplus_cr":      v(("Retained Earnings",)),
                })
        except Exception as e:
            logger.warning("yfinance.balance_sheet.failed", error=str(e))

        return rows

    def _fetch_cash_flows(
        self, ticker: yf.Ticker, years: int
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            # yfinance 0.2.x: .cashflow → .cash_flow
            cf = getattr(ticker, "cash_flow", None)
            if not isinstance(cf, pd.DataFrame) or cf.empty:
                cf = getattr(ticker, "cashflow", pd.DataFrame())
            if not isinstance(cf, pd.DataFrame) or cf.empty:
                return rows

            for col in list(cf.columns)[:years]:
                col_ts = pd.Timestamp(col)

                def gv(*keys: str, _col=col) -> Any:
                    for key in keys:
                        if key in cf.index:
                            val = cf.loc[key, _col]
                            if pd.notna(val):
                                return float(val)
                    return None

                def v(s, _col=col):
                    for key in s:
                        if key in cf.index:
                            val = cf.loc[key, _col]
                            if pd.notna(val):
                                return _to_cr(float(val))
                    return None

                cfo  = v(("Operating Cash Flow",))
                cfi  = v(("Investing Cash Flow",))
                cff  = v(("Financing Cash Flow",))
                capex_raw = gv("Capital Expenditure", "Purchase Of PPE")
                capex = _to_cr(abs(capex_raw) if capex_raw is not None else None)

                fcf = v(("Free Cash Flow",))
                if fcf is None and cfo and capex:
                    fcf = _to_dec(float(cfo) - float(capex))

                rows.append({
                    "period_type": "annual",
                    "period_year": _fiscal_year(col_ts),
                    "period_quarter": None,
                    "cfo_cr":              cfo,
                    "cfi_cr":              cfi,
                    "cff_cr":              cff,
                    "capex_cr":            capex,
                    "free_cash_flow_cr":   fcf,
                    "net_change_in_cash_cr": v(("Changes In Cash",)),
                })
        except Exception as e:
            logger.warning("yfinance.cashflow.failed", error=str(e))

        return rows

    # ── Quarterly fetch methods ───────────────────────────────────────────────

    def fetch_quarterly(self, nse_symbol: str, num_quarters: int = 8) -> FetchResult:
        """
        Fetch last *num_quarters* quarterly P&L, balance sheet, and cash flow.
        Returns a FetchResult whose income_statements / balance_sheets / cash_flows
        all have period_type="quarterly" and period_quarter=1-4.

        yfinance provides up to 4 trailing quarters for free accounts.
        """
        ticker_symbol = f"{nse_symbol}.NS"
        logger.info("yfinance.quarterly.start", symbol=ticker_symbol)

        result = FetchResult(
            nse_symbol=nse_symbol,
            company={},
            income_statements=[],
            balance_sheets=[],
            cash_flows=[],
        )

        try:
            ticker = yf.Ticker(ticker_symbol)
            result.income_statements = self._fetch_quarterly_income(ticker, num_quarters)
            time.sleep(self.delay)
            result.balance_sheets = self._fetch_quarterly_balance_sheets(ticker, num_quarters)
            time.sleep(self.delay)
            result.cash_flows = self._fetch_quarterly_cash_flows(ticker, num_quarters)

            # Minimal company stub so FetchResult.success works
            result.company = {"name": nse_symbol, "nse_symbol": nse_symbol}

            # ── Currency conversion (USD-reporting companies) ─────────────
            try:
                fin_currency = (ticker.info or {}).get("financialCurrency", "INR")
            except Exception:
                fin_currency = "INR"
            if fin_currency and fin_currency != "INR":
                fx = _get_usd_inr_rate()
                logger.info(
                    "yfinance.quarterly.currency.converting",
                    symbol=ticker_symbol,
                    from_currency=fin_currency,
                    usd_inr=round(fx, 2),
                )
                result.income_statements = _apply_currency_fx(result.income_statements, fx)
                result.balance_sheets    = _apply_currency_fx(result.balance_sheets,    fx)
                result.cash_flows        = _apply_currency_fx(result.cash_flows,        fx)

            logger.info(
                "yfinance.quarterly.complete",
                symbol=ticker_symbol,
                income_rows=len(result.income_statements),
                bs_rows=len(result.balance_sheets),
                cf_rows=len(result.cash_flows),
            )
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            result.errors.append(error_msg)
            logger.error("yfinance.quarterly.failed", symbol=ticker_symbol, error=error_msg)

        return result

    def _fetch_quarterly_income(
        self, ticker: yf.Ticker, num_quarters: int
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            fin = getattr(ticker, "quarterly_income_stmt", None)
            if not isinstance(fin, pd.DataFrame) or fin.empty:
                fin = getattr(ticker, "quarterly_financials", pd.DataFrame())
            if not isinstance(fin, pd.DataFrame) or fin.empty:
                return rows

            for col in list(fin.columns)[:num_quarters]:
                col_ts = pd.Timestamp(col)
                fy, q = _fiscal_quarter(col_ts)

                def gv(*keys: str, _col=col) -> Any:
                    for key in keys:
                        if key in fin.index:
                            val = fin.loc[key, _col]
                            if pd.notna(val):
                                return float(val)
                    return None

                revenue   = _to_cr(gv("Total Revenue", "Operating Revenue"))
                ebitda    = _to_cr(gv("EBITDA", "Normalized EBITDA"))
                pat       = _to_cr(gv("Net Income", "Net Income Common Stockholders"))
                dep       = _to_cr(gv("Reconciled Depreciation", "Depreciation And Amortization In Income Statement"))
                ebit      = _to_cr(gv("EBIT", "Operating Income"))
                interest_raw = gv("Interest Expense Non Operating", "Net Interest Income")
                interest  = _to_cr(abs(interest_raw) if interest_raw else None)
                tax_raw   = gv("Tax Provision")
                tax       = _to_cr(abs(tax_raw) if tax_raw else None)
                pbt       = _to_cr(gv("Pretax Income"))
                total_exp = _to_cr(gv("Total Expenses", "Operating Expense"))
                eps_basic   = _to_dec(gv("Basic EPS", "Basic Earnings Per Share"))
                eps_diluted = _to_dec(gv("Diluted EPS", "Diluted Earnings Per Share"))

                rows.append({
                    "period_type":    "quarterly",
                    "period_year":    fy,
                    "period_quarter": q,
                    "revenue_cr":     revenue,
                    "ebitda_cr":      ebitda,
                    "pat_cr":         pat,
                    "depreciation_cr": dep,
                    "ebit_cr":        ebit,
                    "interest_cr":    interest,
                    "pbt_cr":         pbt,
                    "tax_cr":         tax,
                    "total_expenses_cr": total_exp,
                    "eps_basic":      eps_basic,
                    "eps_diluted":    eps_diluted,
                    "dividend_per_share": None,
                })
        except Exception as e:
            logger.warning("yfinance.quarterly_income.failed", error=str(e))

        return rows

    def _fetch_quarterly_balance_sheets(
        self, ticker: yf.Ticker, num_quarters: int
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            bs = getattr(ticker, "quarterly_balance_sheet", None)
            if not isinstance(bs, pd.DataFrame) or bs.empty:
                return rows

            for col in list(bs.columns)[:num_quarters]:
                col_ts = pd.Timestamp(col)
                fy, q = _fiscal_quarter(col_ts)

                def v(keys, _col=col):
                    for key in keys:
                        if key in bs.index:
                            val = bs.loc[key, _col]
                            if pd.notna(val):
                                return _to_cr(float(val))
                    return None

                rows.append({
                    "period_type":    "quarterly",
                    "period_year":    fy,
                    "period_quarter": q,
                    "total_assets_cr":         v(("Total Assets",)),
                    "fixed_assets_cr":          v(("Net PPE", "Net Property Plant Equipment")),
                    "current_assets_cr":        v(("Current Assets",)),
                    "cash_cr":                  v(("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")),
                    "inventories_cr":           v(("Inventory",)),
                    "receivables_cr":           v(("Receivables", "Accounts Receivable")),
                    "investments_cr":           v(("Investments And Advances", "Long Term Investments")),
                    "total_liabilities_cr":     v(("Total Liabilities Net Minority Interest", "Total Liabilities")),
                    "long_term_debt_cr":        v(("Long Term Debt", "Long Term Debt And Capital Lease Obligation")),
                    "short_term_debt_cr":       v(("Current Debt", "Current Debt And Capital Lease Obligation")),
                    "current_liabilities_cr":   v(("Current Liabilities",)),
                    "trade_payables_cr":        v(("Payables And Accrued Expenses", "Accounts Payable")),
                    "shareholders_equity_cr":   v(("Stockholders Equity", "Total Equity Gross Minority Interest")),
                    "share_capital_cr":         v(("Capital Stock", "Common Stock")),
                    "reserves_surplus_cr":      v(("Retained Earnings",)),
                })
        except Exception as e:
            logger.warning("yfinance.quarterly_balance_sheet.failed", error=str(e))

        return rows

    def _fetch_quarterly_cash_flows(
        self, ticker: yf.Ticker, num_quarters: int
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            cf = getattr(ticker, "quarterly_cash_flow", None)
            if not isinstance(cf, pd.DataFrame) or cf.empty:
                return rows

            for col in list(cf.columns)[:num_quarters]:
                col_ts = pd.Timestamp(col)
                fy, q = _fiscal_quarter(col_ts)

                def gv(*keys: str, _col=col) -> Any:
                    for key in keys:
                        if key in cf.index:
                            val = cf.loc[key, _col]
                            if pd.notna(val):
                                return float(val)
                    return None

                def v(keys, _col=col):
                    for key in keys:
                        if key in cf.index:
                            val = cf.loc[key, _col]
                            if pd.notna(val):
                                return _to_cr(float(val))
                    return None

                cfo = v(("Operating Cash Flow",))
                cfi = v(("Investing Cash Flow",))
                cff = v(("Financing Cash Flow",))
                capex_raw = gv("Capital Expenditure", "Purchase Of PPE")
                capex = _to_cr(abs(capex_raw) if capex_raw is not None else None)
                fcf = v(("Free Cash Flow",))
                if fcf is None and cfo and capex:
                    fcf = _to_dec(float(cfo) - float(capex))

                rows.append({
                    "period_type":    "quarterly",
                    "period_year":    fy,
                    "period_quarter": q,
                    "cfo_cr":              cfo,
                    "cfi_cr":              cfi,
                    "cff_cr":              cff,
                    "capex_cr":            capex,
                    "free_cash_flow_cr":   fcf,
                    "net_change_in_cash_cr": v(("Changes In Cash",)),
                })
        except Exception as e:
            logger.warning("yfinance.quarterly_cashflow.failed", error=str(e))

        return rows


def compute_key_ratios(
    company_info: dict,
    income_statements: list[dict],
    balance_sheets: list[dict],
    cash_flows: list[dict],
) -> list[dict[str, Any]]:
    """
    Compute key financial ratios for each annual period.

    Ratios are derived from the raw financial statements.
    Requires at least 2 years of income statements to compute growth metrics.
    """
    ratios: list[dict[str, Any]] = []

    # Index by fiscal year for cross-statement lookups
    bs_by_year   = {r["period_year"]: r for r in balance_sheets}
    cf_by_year   = {r["period_year"]: r for r in cash_flows}
    pl_by_year   = {r["period_year"]: r for r in income_statements}
    cmp          = float(company_info.get("cmp") or 0)

    sorted_years = sorted(pl_by_year.keys(), reverse=True)

    for i, year in enumerate(sorted_years):
        pl  = pl_by_year[year]
        bs  = bs_by_year.get(year, {})
        cf  = cf_by_year.get(year, {})
        prev_pl = pl_by_year.get(sorted_years[i + 1]) if i + 1 < len(sorted_years) else None

        def f(d, k): return float(d.get(k) or 0) or None

        revenue     = f(pl, "revenue_cr")
        pat         = f(pl, "pat_cr")
        ebitda      = f(pl, "ebitda_cr")
        ebit        = f(pl, "ebit_cr")
        equity      = f(bs, "shareholders_equity_cr")
        # Fall back to share_capital + reserves when equity not directly stored
        # (Screener.in older years may only have reserves_surplus_cr)
        if equity is None:
            sc  = f(bs, "share_capital_cr") or 0
            res = f(bs, "reserves_surplus_cr")
            if res is not None:
                equity = sc + res
        total_assets = f(bs, "total_assets_cr")
        total_debt  = (f(bs, "long_term_debt_cr") or 0) + (f(bs, "short_term_debt_cr") or 0)
        cur_assets  = f(bs, "current_assets_cr")
        cur_liab    = f(bs, "current_liabilities_cr")
        inventory   = f(bs, "inventories_cr")
        receivables = f(bs, "receivables_cr")
        payables    = f(bs, "trade_payables_cr")
        interest    = f(pl, "interest_cr")
        market_cap  = f(company_info, "market_cap_cr")

        eps_basic   = float(pl.get("eps_basic") or 0) or None

        # ── Profitability ──────────────────────────────────────────────────
        roe   = _ratio(pat, equity, pct=True)
        roa   = _ratio(pat, total_assets, pct=True)
        ebitda_margin = _ratio(ebitda, revenue, pct=True)
        npm   = _ratio(pat, revenue, pct=True)

        # ROCE = EBIT / Capital Employed (Total Assets - Current Liabilities)
        cap_employed = (total_assets or 0) - (cur_liab or 0)
        roce  = _ratio(ebit or pat, cap_employed, pct=True) if cap_employed else None

        # ── Valuation ──────────────────────────────────────────────────────
        pe    = _ratio(cmp, eps_basic) if cmp and eps_basic else None

        # P/B = Market Cap / Shareholders Equity
        pb    = _ratio(market_cap, equity) if market_cap and equity else None

        # EV/EBITDA (simple: market cap as proxy for EV)
        ev_ebitda = _ratio(market_cap, ebitda) if market_cap and ebitda else None

        # P/Sales
        ps    = _ratio(market_cap, revenue) if market_cap and revenue else None

        # ── Financial Health ───────────────────────────────────────────────
        de    = _ratio(total_debt, equity) if equity else None
        cr    = _ratio(cur_assets, cur_liab) if cur_liab else None
        quick = _ratio((cur_assets or 0) - (inventory or 0), cur_liab) if cur_liab else None
        ic    = _ratio(ebit or pat, interest) if interest else None

        # ── Efficiency ────────────────────────────────────────────────────
        asset_turn = _ratio(revenue, total_assets)
        inv_days   = _ratio((inventory or 0) * 365, revenue) if revenue and inventory else None
        rec_days   = _ratio((receivables or 0) * 365, revenue) if revenue and receivables else None
        pay_days   = _ratio((payables or 0) * 365, revenue) if revenue and payables else None
        ccc = None
        if inv_days and rec_days and pay_days:
            ccc = _d(inv_days + rec_days - pay_days)

        # ── Growth (YoY) ──────────────────────────────────────────────────
        rev_prev   = float(prev_pl.get("revenue_cr") or 0) if prev_pl else None
        pat_prev   = float(prev_pl.get("pat_cr") or 0) if prev_pl else None
        eps_prev   = float(prev_pl.get("eps_basic") or 0) if prev_pl else None

        rev_growth = _growth(revenue, rev_prev)
        pat_growth = _growth(pat, pat_prev)
        eps_growth = _growth(eps_basic, eps_prev)

        ratios.append({
            "period_type":              "annual",
            "period_year":              year,
            "roe_pct":                  _d(roe),
            "roce_pct":                 _d(roce),
            "roa_pct":                  _d(roa),
            "ebitda_margin_pct":        _d(ebitda_margin),
            "net_profit_margin_pct":    _d(npm),
            "pe_ratio":                 _d(pe),
            "pb_ratio":                 _d(pb),
            "ps_ratio":                 _d(ps),
            "ev_ebitda":                _d(ev_ebitda),
            "dividend_yield_pct":       None,
            "debt_equity_ratio":        _d(de),
            "current_ratio":            _d(cr),
            "quick_ratio":              _d(quick),
            "interest_coverage":        _d(ic),
            "asset_turnover":           _d(asset_turn),
            "inventory_days":           _d(inv_days),
            "receivables_days":         _d(rec_days),
            "payables_days":            _d(pay_days),
            "cash_conversion_cycle":    ccc,
            "revenue_growth_pct":       _d(rev_growth),
            "pat_growth_pct":           _d(pat_growth),
            "eps_growth_pct":           _d(eps_growth),
        })

    return ratios


# ── Internal helpers ──────────────────────────────────────────────────────────

def _col_idx(df: pd.DataFrame, col) -> int:
    """Return the integer column index for a given column label."""
    try:
        return list(df.columns).index(col)
    except ValueError:
        return 0


def _ratio(numerator, denominator, pct: bool = False) -> float | None:
    if not numerator or not denominator or denominator == 0:
        return None
    r = float(numerator) / float(denominator)
    return r * 100 if pct else r


def _growth(current, previous) -> float | None:
    if not current or not previous or previous == 0:
        return None
    return ((float(current) - float(previous)) / abs(float(previous))) * 100


def _d(value: float | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(round(value, 2)))
    except InvalidOperation:
        return None
