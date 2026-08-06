#!/usr/bin/env python3
"""
Fetch Nifty 500 index constituents from NSE India API.

Usage:
    python -m scripts.fetch_nifty500          # print as Python list
    python -m scripts.fetch_nifty500 --json   # output JSON
    python -m scripts.fetch_nifty500 --csv    # output CSV

Output: list of (nse_symbol, isin, company_name, series, industry)

NSE API notes:
  - Requires a cookie from the NSE homepage (session-based)
  - Rate-limited — add 1-2s delay between calls
  - Returns JSON with 'data' key containing all constituents
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import httpx

NSE_BASE = "https://www.nseindia.com"
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/market-data/live-equity-market",
    "Connection": "keep-alive",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
}

INDEX_URL = (
    "https://www.nseindia.com/api/equity-stockIndices"
    "?index=NIFTY%20500"
)

# Fallback: NSE archives CSV (more stable URL)
CSV_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"


def fetch_nifty500() -> list[dict]:
    """
    Fetch Nifty 500 constituents.

    Tries NSE equity-stockIndices API first; falls back to NSE archives CSV.
    Returns list of dicts with keys: symbol, name, isin, industry, series
    """
    with httpx.Client(headers=NSE_HEADERS, timeout=30, follow_redirects=True) as client:
        # ── Strategy 1: NSE archives CSV (most reliable) ──────────────────
        print("Fetching Nifty 500 from NSE archives CSV...", file=sys.stderr)
        try:
            resp = client.get(CSV_URL)
            if resp.status_code == 200:
                lines = resp.text.strip().splitlines()
                # Format: Company Name,Industry,Symbol,Series,ISIN Code
                constituents = []
                for line in lines[1:]:   # skip header
                    parts = line.split(",")
                    if len(parts) < 5:
                        continue
                    constituents.append({
                        "name":     parts[0].strip().strip('"'),
                        "industry": parts[1].strip().strip('"'),
                        "symbol":   parts[2].strip().strip('"'),
                        "series":   parts[3].strip().strip('"'),
                        "isin":     parts[4].strip().strip('"'),
                    })
                if constituents:
                    print(f"Found {len(constituents)} constituents from CSV.", file=sys.stderr)
                    return constituents
        except Exception as e:
            print(f"CSV fetch failed: {e}", file=sys.stderr)

        # ── Strategy 2: NSE API (requires session) ────────────────────────
        print("Trying NSE API (requires session)...", file=sys.stderr)
        r = client.get(NSE_BASE)
        r.raise_for_status()
        time.sleep(2)
        r2 = client.get("https://www.nseindia.com/market-data/live-equity-market")
        r2.raise_for_status()
        time.sleep(2)

        resp = client.get(INDEX_URL)
        resp.raise_for_status()

        payload = resp.json()
        data = payload.get("data", [])
        constituents = []
        for row in data:
            symbol = row.get("symbol", "").strip()
            if not symbol or symbol == "NIFTY 500":
                continue
            constituents.append({
                "symbol":   symbol,
                "name":     row.get("meta", {}).get("companyName", row.get("companyName", "")),
                "isin":     row.get("meta", {}).get("isin", row.get("isinCode", "")),
                "industry": row.get("meta", {}).get("industry", row.get("industry", "")),
                "series":   row.get("series", "EQ"),
            })
        print(f"Found {len(constituents)} constituents from API.", file=sys.stderr)
        return constituents


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Nifty 500 from NSE")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--csv",  action="store_true", help="Output as CSV")
    args = parser.parse_args()

    data = fetch_nifty500()

    if args.json:
        print(json.dumps(data, indent=2))
    elif args.csv:
        print("symbol,name,isin,industry,series")
        for d in data:
            name = d["name"].replace(",", " ")
            print(f"{d['symbol']},{name},{d['isin']},{d['industry']},{d['series']}")
    else:
        print("NIFTY_500 = [")
        for d in data:
            name = d["name"].replace('"', "'")
            print(f'    ("{d["symbol"]}", "{d["isin"]}", "{name}"),')
        print("]")


if __name__ == "__main__":
    main()
