"""
Screener.in data fetcher.

Screener.in has no official API, but its company pages have consistent
structured HTML that we can parse reliably.

What Screener.in provides that yfinance does NOT:
  - Accurate promoter / FII / DII holding percentages
  - BSE code
  - Peer comparison list
  - Indian-standard financial layout (Sales, OPM%, PAT, EPS)
  - Quarterly results in Indian format

Usage:
    fetcher = ScreenerFetcher()
    data = fetcher.fetch_holding_data("TCS")
    # Returns {"promoter_holding_pct": 72.3, "fii_holding_pct": 12.1, ...}

Rate limiting:
    Screener.in is a community platform. Be respectful.
    Default delay is 3 seconds between requests.
    Do NOT run concurrent requests to Screener.in.

Terms:
    Screener.in allows personal/educational use.
    Do not resell the data or use it for commercial scraping at scale.
"""
from __future__ import annotations

import re
import time
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from bs4 import BeautifulSoup

import structlog

logger = structlog.get_logger(__name__)

SCREENER_BASE = "https://www.screener.in"
REQUEST_DELAY = 3.0     # seconds between requests
TIMEOUT       = 15      # request timeout seconds

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.screener.in/",
    "Connection": "keep-alive",
}


class ScreenerFetcher:
    """Fetches supplementary data from Screener.in for Indian companies."""

    def __init__(self, delay: float = REQUEST_DELAY) -> None:
        self.delay = delay
        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    def _get_company_page(
        self, nse_symbol: str, bse_code: str | None = None
    ) -> "requests.Response | None":
        """
        Fetch the Screener.in company page, trying multiple URL patterns.

        Some companies (e.g. LTIM, TATAMOTORS) are indexed by BSE code on
        Screener.in instead of NSE symbol.  We try four URLs in priority order:
          1. /company/{nse_symbol}/consolidated/
          2. /company/{nse_symbol}/
          3. /company/{bse_code}/consolidated/   (if bse_code given)
          4. /company/{bse_code}/               (if bse_code given)
        """
        slugs: list[str] = [nse_symbol]
        if bse_code:
            slugs.append(bse_code)

        for slug in slugs:
            for suffix in ["/consolidated/", "/"]:
                url = f"{SCREENER_BASE}/company/{slug}{suffix}"
                try:
                    resp = self._session.get(url, timeout=TIMEOUT)
                    time.sleep(self.delay)
                    if resp.status_code == 200:
                        logger.info("screener.page.found", symbol=nse_symbol, url=url)
                        return resp
                except Exception as exc:
                    logger.warning("screener.page.error", symbol=nse_symbol, url=url, error=str(exc))

        logger.warning("screener.page.not_found", symbol=nse_symbol, bse_code=bse_code)
        return None

    def fetch_holding_data(
        self, nse_symbol: str, bse_code: str | None = None
    ) -> dict[str, Any]:
        """
        Fetch shareholding data from Screener.in.

        Returns:
            {
                "promoter_holding_pct": Decimal | None,
                "fii_holding_pct":      Decimal | None,
                "dii_holding_pct":      Decimal | None,
                "public_holding_pct":   Decimal | None,
                "bse_code":             str | None,
            }
        """
        result: dict[str, Any] = {
            "promoter_holding_pct": None,
            "fii_holding_pct":      None,
            "dii_holding_pct":      None,
            "public_holding_pct":   None,
            "bse_code":             None,
        }

        resp = self._get_company_page(nse_symbol, bse_code)
        try:
            if resp is None or resp.status_code != 200:
                logger.warning(
                    "screener.fetch.failed",
                    symbol=nse_symbol,
                )
                return result

            soup = BeautifulSoup(resp.text, "html.parser")

            # ── BSE code ──────────────────────────────────────────────────
            result["bse_code"] = self._extract_bse_code(soup)

            # ── Shareholding ──────────────────────────────────────────────
            holdings = self._extract_shareholding(soup)
            result.update(holdings)

            logger.info("screener.fetch.success", symbol=nse_symbol, data=result)

        except Exception as exc:
            logger.warning("screener.fetch.error", symbol=nse_symbol, error=str(exc))

        return result

    def _extract_bse_code(self, soup: BeautifulSoup) -> str | None:
        """Extract BSE code from the company page."""
        try:
            # Screener shows BSE/NSE links in the company header
            for a in soup.select("a[href*='bseindia.com']"):
                href = a.get("href", "")
                # BSE URLs contain the scrip code: /stock-share-price/COMPANY/500325/
                parts = [p for p in href.split("/") if p.isdigit() and len(p) == 6]
                if parts:
                    return parts[0]
        except Exception:
            pass
        return None

    def _extract_shareholding(self, soup: BeautifulSoup) -> dict[str, Decimal | None]:
        """
        Extract promoter, FII, DII, public holding percentages.

        Screener renders the latest shareholding pattern in a dedicated section.
        """
        result: dict[str, Decimal | None] = {
            "promoter_holding_pct": None,
            "fii_holding_pct":      None,
            "dii_holding_pct":      None,
            "public_holding_pct":   None,
        }
        try:
            # Screener.in shareholding table has class "data-table"
            # under a section with id="shareholding"
            section = soup.find("section", {"id": "shareholding"})
            if not section:
                return result

            table = section.find("table")
            if not table:
                return result

            rows = table.find_all("tr")
            if len(rows) < 2:
                return result

            # Header row has quarter dates; we want the latest (first data column)
            for row in rows[1:]:    # skip header
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                label = cells[0].get_text(strip=True).lower()
                # Latest value is the second cell (most recent quarter)
                value_text = cells[1].get_text(strip=True).replace("%", "").strip()
                try:
                    value = Decimal(value_text)
                except Exception:
                    continue

                if "promoter" in label:
                    result["promoter_holding_pct"] = value
                elif "fii" in label or "foreign" in label:
                    result["fii_holding_pct"] = value
                elif "dii" in label or "domestic" in label or "mutual" in label:
                    result["dii_holding_pct"] = value
                elif "public" in label or "retail" in label:
                    result["public_holding_pct"] = value

        except Exception as exc:
            logger.warning("screener.shareholding.parse_error", error=str(exc))

        return result

    # ── Financial statement scraping ──────────────────────────────────────────

    @staticmethod
    def _parse_screener_period(header: str) -> int | None:
        """
        Convert a Screener.in column header to an Indian fiscal year integer.

        "Mar 2024" → 2024  (FY ending March 2024)
        "Mar 2023" → 2023
        Returns None for "TTM" or unparseable headers.
        """
        header = header.strip()
        if header.upper() in ("TTM", ""):
            return None
        m = re.match(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})", header)
        if not m:
            return None
        return int(m.group(2))

    @staticmethod
    def _parse_num(text: str) -> Decimal | None:
        """Parse Screener.in numeric cell: "1,23,456.78" | "-" | "" → Decimal | None."""
        text = text.strip().replace(",", "")
        if not text or text in ("-", "--", "NA", "N/A", "0"):
            return None
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            return None

    def _extract_section_rows(
        self, soup: BeautifulSoup, section_id: str
    ) -> tuple[list[str], dict[str, list[str]]]:
        """
        Parse a Screener.in financial table section.

        Returns:
            (period_headers, {row_label: [cell_text, ...]})
        """
        section = soup.find("section", {"id": section_id})
        if not section:
            return [], {}

        table = section.find("table", class_="data-table") or section.find("table")
        if not table:
            return [], {}

        thead = table.find("thead")
        tbody = table.find("tbody")
        if not thead or not tbody:
            return [], {}

        # Column headers (skip the first empty th)
        headers: list[str] = [
            th.get_text(strip=True)
            for th in thead.find_all("th")[1:]
        ]

        # Row data
        rows: dict[str, list[str]] = {}
        for tr in tbody.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            # Strip trailing " +" tooltip markers from labels
            label = re.sub(r"\s*\+\s*$", "", cells[0].get_text(strip=True)).strip()
            values = [
                cells[i].get_text(strip=True) if i < len(cells) else ""
                for i in range(1, len(headers) + 1)
            ]
            rows[label] = values

        return headers, rows

    def _rows_to_annual_pl(
        self, headers: list[str], rows: dict[str, list[str]]
    ) -> list[dict[str, Any]]:
        """Convert parsed Screener P&L table rows → income_statement dicts."""
        results = []
        for i, header in enumerate(headers):
            fy = self._parse_screener_period(header)
            if fy is None:
                continue

            def v(label: str) -> Decimal | None:
                row = rows.get(label, [])
                return self._parse_num(row[i]) if i < len(row) else None

            revenue = v("Sales") or v("Revenue from Operations") or v("Net Sales")
            ebitda  = v("Operating Profit")
            other   = v("Other Income")
            dep     = v("Depreciation")
            interest= v("Interest") or v("Finance Cost")
            pbt     = v("Profit before tax") or v("PBT")
            pat     = v("Net Profit") or v("PAT")
            eps     = v("EPS in Rs") or v("EPS (Rs)") or v("Basic EPS (Rs)")

            if revenue is None and pat is None:
                continue  # skip empty columns

            results.append({
                "period_type":    "annual",
                "period_year":    fy,
                "period_quarter": None,
                "revenue_cr":     revenue,
                "ebitda_cr":      ebitda,
                "other_income_cr":other,
                "depreciation_cr":dep,
                "interest_cr":    interest,
                "pbt_cr":         pbt,
                "pat_cr":         pat,
                "eps_basic":      eps,
            })
        return results

    def _rows_to_annual_bs(
        self, headers: list[str], rows: dict[str, list[str]]
    ) -> list[dict[str, Any]]:
        """Convert parsed Screener Balance Sheet rows → balance_sheet dicts."""
        results = []
        for i, header in enumerate(headers):
            fy = self._parse_screener_period(header)
            if fy is None:
                continue

            def v(label: str) -> Decimal | None:
                row = rows.get(label, [])
                return self._parse_num(row[i]) if i < len(row) else None

            equity    = (v("Share Capital") or v("Equity Share Capital")
                         or v("Paid Up Capital") or v("Equity Capital"))
            reserves  = v("Reserves") or v("Reserves & Surplus")
            borrowings= v("Borrowings") or v("Total Borrowings")
            t_assets  = v("Total Assets") or v("Total Assets ")
            fixed     = v("Fixed Assets") or v("Net Block")
            invest    = v("Investments")
            cur_assets= v("Current Assets") or v("Total Current Assets")

            # Compute shareholders_equity; fall back to reserves alone if
            # share capital label is missing (common in consolidated sheets)
            if equity is not None and reserves is not None:
                shareholders_equity = equity + reserves
            elif reserves is not None:
                shareholders_equity = (equity or Decimal("0")) + reserves
            else:
                shareholders_equity = equity

            if t_assets is None and shareholders_equity is None:
                continue

            results.append({
                "period_type":           "annual",
                "period_year":           fy,
                "period_quarter":        None,
                "total_assets_cr":       t_assets,
                "fixed_assets_cr":       fixed,
                "current_assets_cr":     cur_assets,
                "investments_cr":        invest,
                "long_term_debt_cr":     borrowings,
                "shareholders_equity_cr":shareholders_equity,
                "share_capital_cr":      equity,
                "reserves_surplus_cr":   reserves,
            })
        return results

    def _rows_to_annual_cf(
        self, headers: list[str], rows: dict[str, list[str]]
    ) -> list[dict[str, Any]]:
        """Convert parsed Screener Cash Flow rows → cash_flow dicts."""
        results = []
        for i, header in enumerate(headers):
            fy = self._parse_screener_period(header)
            if fy is None:
                continue

            def v(label: str) -> Decimal | None:
                row = rows.get(label, [])
                return self._parse_num(row[i]) if i < len(row) else None

            cfo = v("Cash from Operating Activity") or v("Operating Cash Flow")
            cfi = v("Cash from Investing Activity") or v("Investing Cash Flow")
            cff = v("Cash from Financing Activity") or v("Financing Cash Flow")
            net = v("Net Cash Flow")

            if cfo is None:
                continue

            results.append({
                "period_type":        "annual",
                "period_year":        fy,
                "period_quarter":     None,
                "cfo_cr":             cfo,
                "cfi_cr":             cfi,
                "cff_cr":             cff,
                "net_change_in_cash_cr": net,
            })
        return results

    def fetch_financials(
        self, nse_symbol: str, bse_code: str | None = None
    ) -> dict[str, Any]:
        """
        Scrape 10+ years of annual financial statements from Screener.in.

        Returns dict with keys: income_statements, balance_sheets, cash_flows
        (each a list of dicts in the same format as YFinanceFetcher).
        """
        result: dict[str, Any] = {
            "income_statements": [],
            "balance_sheets":    [],
            "cash_flows":        [],
        }

        resp = self._get_company_page(nse_symbol, bse_code)
        if resp is None:
            logger.warning("screener.financials.not_found", symbol=nse_symbol)
            return result

        try:
            soup = BeautifulSoup(resp.text, "html.parser")

            pl_headers, pl_rows = self._extract_section_rows(soup, "profit-loss")
            bs_headers, bs_rows = self._extract_section_rows(soup, "balance-sheet")
            cf_headers, cf_rows = self._extract_section_rows(soup, "cash-flow")

            result["income_statements"] = self._rows_to_annual_pl(pl_headers, pl_rows)
            result["balance_sheets"]    = self._rows_to_annual_bs(bs_headers, bs_rows)
            result["cash_flows"]        = self._rows_to_annual_cf(cf_headers, cf_rows)

            logger.info(
                "screener.financials.success",
                symbol=nse_symbol,
                income=len(result["income_statements"]),
                bs=len(result["balance_sheets"]),
                cf=len(result["cash_flows"]),
            )
        except Exception as exc:
            logger.warning("screener.financials.parse_error", symbol=nse_symbol, error=str(exc))

        return result

    def close(self) -> None:
        self._session.close()
