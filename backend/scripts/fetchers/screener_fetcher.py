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

import time
from decimal import Decimal
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

    def fetch_holding_data(self, nse_symbol: str) -> dict[str, Any]:
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

        url = f"{SCREENER_BASE}/company/{nse_symbol}/consolidated/"
        try:
            resp = self._session.get(url, timeout=TIMEOUT)
            time.sleep(self.delay)

            if resp.status_code == 404:
                # Try standalone if consolidated doesn't exist
                url = f"{SCREENER_BASE}/company/{nse_symbol}/"
                resp = self._session.get(url, timeout=TIMEOUT)
                time.sleep(self.delay)

            if resp.status_code != 200:
                logger.warning(
                    "screener.fetch.failed",
                    symbol=nse_symbol,
                    status=resp.status_code,
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

    def close(self) -> None:
        self._session.close()
