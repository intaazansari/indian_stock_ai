#!/usr/bin/env python3
"""
Database seeding script — populates Nifty 50 companies with financial data.

Data sources:
  1. Yahoo Finance (yfinance) — company info + 5-year annual financials
  2. Screener.in              — promoter/FII/DII shareholding + BSE code
  3. Key ratios               — computed locally from the fetched statements

Usage (run from the backend/ directory):

    # Seed all 50 Nifty companies (takes ~10-15 minutes due to rate limits)
    python -m scripts.seed_db

    # Seed specific companies only
    python -m scripts.seed_db --symbols TCS INFY RELIANCE

    # Seed with more years of history (default 5)
    python -m scripts.seed_db --years 10

    # Skip Screener.in (faster, but no promoter holding data)
    python -m scripts.seed_db --no-screener

    # Dry run — fetch data but do not write to DB
    python -m scripts.seed_db --dry-run

Prerequisites:
    1. PostgreSQL running (docker-compose up -d postgres)
    2. Alembic migrations applied (alembic upgrade head)
    3. .env file present in backend/ or parent directory
    4. pip install -r requirements.txt
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

# ── Ensure backend/ is in sys.path when run as a module ──────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

import csv

# Load .env before importing app modules
from dotenv import load_dotenv  # type: ignore[import]
_env_path = Path(__file__).parent.parent / ".env"
if not _env_path.exists():
    _env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path)

import structlog
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tabulate import tabulate
from tqdm import tqdm

from app.core.config import settings
from app.core.logging import setup_logging
from app.models import (
    AnalysisCache, BalanceSheet, CashFlow, Company,
    IncomeStatement, KeyRatio, Portfolio, User, Watchlist,
)
from app.db.base import Base
from scripts.fetchers.yfinance_fetcher import (
    YFinanceFetcher, FetchResult, compute_key_ratios,
)
from scripts.fetchers.screener_fetcher import ScreenerFetcher

setup_logging()
logger = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Nifty 50 company list  (as of Dec 2024)
# Format: (NSE Symbol, BSE Code, Display Name)
# ─────────────────────────────────────────────────────────────────────────────
NIFTY_50: list[tuple[str, str, str]] = [
    ("ADANIENT",   "512599", "Adani Enterprises"),
    ("ADANIPORTS", "532921", "Adani Ports and SEZ"),
    ("APOLLOHOSP", "508869", "Apollo Hospitals Enterprise"),
    ("ASIANPAINT", "500820", "Asian Paints"),
    ("AXISBANK",   "532215", "Axis Bank"),
    ("BAJAJ-AUTO", "532977", "Bajaj Auto"),
    ("BAJFINANCE", "500034", "Bajaj Finance"),
    ("BAJAJFINSV", "532978", "Bajaj Finserv"),
    ("BPCL",       "500547", "Bharat Petroleum Corporation"),
    ("BHARTIARTL", "532454", "Bharti Airtel"),
    ("BRITANNIA",  "500825", "Britannia Industries"),
    ("CIPLA",      "500087", "Cipla"),
    ("COALINDIA",  "533278", "Coal India"),
    ("DIVISLAB",   "532488", "Divi's Laboratories"),
    ("DRREDDY",    "500124", "Dr. Reddy's Laboratories"),
    ("EICHERMOT",  "505200", "Eicher Motors"),
    ("GRASIM",     "500300", "Grasim Industries"),
    ("HCLTECH",    "532281", "HCL Technologies"),
    ("HDFCBANK",   "500180", "HDFC Bank"),
    ("HDFCLIFE",   "540777", "HDFC Life Insurance Company"),
    ("HEROMOTOCO", "500182", "Hero MotoCorp"),
    ("HINDALCO",   "500440", "Hindalco Industries"),
    ("HINDUNILVR", "500696", "Hindustan Unilever"),
    ("ICICIBANK",  "532174", "ICICI Bank"),
    ("ITC",        "500875", "ITC"),
    ("INDUSINDBK", "532187", "IndusInd Bank"),
    ("INFY",       "500209", "Infosys"),
    ("JSWSTEEL",   "500228", "JSW Steel"),
    ("KOTAKBANK",  "500247", "Kotak Mahindra Bank"),
    ("LT",         "500510", "Larsen & Toubro"),
    ("LTIM",       "540005", "LTIMindtree"),
    ("M&M",        "500520", "Mahindra & Mahindra"),
    ("MARUTI",     "532500", "Maruti Suzuki India"),
    ("NTPC",       "532555", "NTPC"),
    ("NESTLEIND",  "500790", "Nestle India"),
    ("ONGC",       "500312", "ONGC"),
    ("POWERGRID",  "532898", "Power Grid Corporation of India"),
    ("RELIANCE",   "500325", "Reliance Industries"),
    ("SBILIFE",    "540719", "SBI Life Insurance Company"),
    ("SHRIRAMFIN", "511218", "Shriram Finance"),
    ("SBIN",       "500112", "State Bank of India"),
    ("SUNPHARMA",  "524715", "Sun Pharmaceutical Industries"),
    ("TCS",        "532540", "Tata Consultancy Services"),
    ("TATACONSUM", "500800", "Tata Consumer Products"),
    ("TATAMOTORS", "500570", "Tata Motors"),
    ("TATASTEEL",  "500470", "Tata Steel"),
    ("TECHM",      "532755", "Tech Mahindra"),
    ("TITAN",      "500114", "Titan Company"),
    ("ULTRACEMCO", "532538", "UltraTech Cement"),
    ("WIPRO",      "507685", "Wipro"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────────────────

async def upsert_company(
    session: AsyncSession,
    data: dict[str, Any],
    bse_code: str | None,
    screener_data: dict[str, Any],
) -> Company:
    """
    Insert or update a company record using PostgreSQL's ON CONFLICT DO UPDATE.
    Safe to run multiple times — won't create duplicates.
    """
    # Merge screener data into company record
    holding_data = {
        "promoter_holding_pct": screener_data.get("promoter_holding_pct") or data.get("promoter_holding_pct"),
        "fii_holding_pct":      screener_data.get("fii_holding_pct"),
        "dii_holding_pct":      screener_data.get("dii_holding_pct"),
        "public_holding_pct":   screener_data.get("public_holding_pct"),
        "bse_code":             screener_data.get("bse_code") or bse_code,
    }

    values = {
        "name":                  data["name"],
        "nse_symbol":            data["nse_symbol"],
        "isin":                  data.get("isin"),
        "sector":                data.get("sector"),
        "industry":              data.get("industry"),
        "description":           data.get("description"),
        "website":               data.get("website"),
        "market_cap_cr":         data.get("market_cap_cr"),
        "cmp":                   data.get("cmp"),
        "face_value":            data.get("face_value"),
        "week52_high":           data.get("week52_high"),
        "week52_low":            data.get("week52_low"),
        "employee_count":        data.get("employee_count"),
        "headquarters":          data.get("headquarters"),
        "updated_at":            datetime.now(timezone.utc),  # always reflect last seed time
        **holding_data,
    }

    stmt = pg_insert(Company).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["nse_symbol"],
        set_={k: stmt.excluded[k] for k in values if k != "nse_symbol"},
    )
    await session.execute(stmt)
    await session.flush()

    result = await session.execute(
        select(Company).where(Company.nse_symbol == data["nse_symbol"])
    )
    return result.scalar_one()


async def upsert_income_statements(
    session: AsyncSession, company_id, rows: list[dict]
) -> int:
    count = 0
    for row in rows:
        if not row.get("revenue_cr") and not row.get("pat_cr"):
            continue   # skip completely empty rows
        stmt = pg_insert(IncomeStatement).values(company_id=company_id, **row)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_income_period",
            set_={k: stmt.excluded[k] for k in row},
        )
        await session.execute(stmt)
        count += 1
    return count


async def upsert_balance_sheets(
    session: AsyncSession, company_id, rows: list[dict]
) -> int:
    count = 0
    for row in rows:
        if not row.get("total_assets_cr"):
            continue
        stmt = pg_insert(BalanceSheet).values(company_id=company_id, **row)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_balance_period",
            set_={k: stmt.excluded[k] for k in row},
        )
        await session.execute(stmt)
        count += 1
    return count


async def upsert_cash_flows(
    session: AsyncSession, company_id, rows: list[dict]
) -> int:
    count = 0
    for row in rows:
        if not row.get("cfo_cr") and not row.get("free_cash_flow_cr"):
            continue
        stmt = pg_insert(CashFlow).values(company_id=company_id, **row)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_cashflow_period",
            set_={k: stmt.excluded[k] for k in row},
        )
        await session.execute(stmt)
        count += 1
    return count


async def upsert_key_ratios(
    session: AsyncSession, company_id, rows: list[dict]
) -> int:
    count = 0
    for row in rows:
        stmt = pg_insert(KeyRatio).values(company_id=company_id, **row)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_ratio_period",
            set_={k: stmt.excluded[k] for k in row},
        )
        await session.execute(stmt)
        count += 1
    return count


# ─────────────────────────────────────────────────────────────────────────────
# Main seed logic
# ─────────────────────────────────────────────────────────────────────────────

async def seed_company(
    session: AsyncSession,
    nse_symbol: str,
    bse_code: str,
    display_name: str,
    years: int,
    use_screener: bool,
    dry_run: bool,
    include_quarterly: bool = False,
    quarterly_only: bool = False,
) -> dict[str, Any]:
    """Fetch and seed data for one company. Returns a status dict."""
    status = {
        "symbol": nse_symbol,
        "name":   display_name,
        "income": 0,
        "bs":     0,
        "cf":     0,
        "ratios": 0,
        "scrn_pl": 0,   # Screener.in income rows
        "scrn_err": "",  # Screener.in error if any
        "status": "ok",
        "error":  "",
    }

    try:
        fetcher = YFinanceFetcher()

        # ── Fast path: company already has annual data, only add quarterly ──
        if quarterly_only:
            result = await session.execute(
                select(Company).where(Company.nse_symbol == nse_symbol)
            )
            company = result.scalar_one_or_none()
            if not company:
                status["status"] = "failed"
                status["error"] = "Company not in DB — run without --skip-existing first"
                return status

            q_result = fetcher.fetch_quarterly(nse_symbol, num_quarters=12)

            if dry_run:
                status["income"] = len(q_result.income_statements)
                status["bs"]     = len(q_result.balance_sheets)
                status["cf"]     = len(q_result.cash_flows)
                status["status"] = "dry-run"
                return status

            status["income"] = await upsert_income_statements(session, company.id, q_result.income_statements)
            status["bs"]     = await upsert_balance_sheets(session, company.id, q_result.balance_sheets)
            status["cf"]     = await upsert_cash_flows(session, company.id, q_result.cash_flows)
            await session.commit()
            return status

        # ── Normal path ──────────────────────────────────────────────────────
        # ── 1. Fetch from Yahoo Finance ────────────────────────────────────
        fetch_result: FetchResult = fetcher.fetch_all(nse_symbol, years=years)

        if not fetch_result.success:
            status["status"] = "failed"
            status["error"] = "; ".join(fetch_result.errors) or "No data returned"
            return status

        # ── 2. Fetch shareholding + historical financials from Screener.in ──
        screener_data: dict[str, Any] = {}
        screener_financials: dict[str, Any] = {"income_statements": [], "balance_sheets": [], "cash_flows": []}
        if use_screener:
            screener = ScreenerFetcher()
            try:
                screener_data = screener.fetch_holding_data(nse_symbol)
                screener_financials = screener.fetch_financials(nse_symbol)
                status["scrn_pl"] = len(screener_financials.get("income_statements", []))
                if status["scrn_pl"] == 0:
                    status["scrn_err"] = "no data"
            except Exception as scrn_exc:
                status["scrn_err"] = str(scrn_exc)[:40]
            finally:
                screener.close()

        # ── 3. Compute key ratios ──────────────────────────────────────────
        ratios = compute_key_ratios(
            company_info=fetch_result.company,
            income_statements=fetch_result.income_statements,
            balance_sheets=fetch_result.balance_sheets,
            cash_flows=fetch_result.cash_flows,
        )

        if dry_run:
            status["income"] = len(fetch_result.income_statements)
            status["bs"]     = len(fetch_result.balance_sheets)
            status["cf"]     = len(fetch_result.cash_flows)
            status["ratios"] = len(ratios)
            status["status"] = "dry-run"
            return status

        # ── 4. Write to database ───────────────────────────────────────────
        company = await upsert_company(
            session, fetch_result.company, bse_code, screener_data
        )
        cid = company.id

        # Upsert Screener.in historical data first (older years, fewer fields).
        # yfinance upsert below will overwrite recent years with richer data.
        if screener_financials["income_statements"]:
            await upsert_income_statements(session, cid, screener_financials["income_statements"])
        if screener_financials["balance_sheets"]:
            await upsert_balance_sheets(session, cid, screener_financials["balance_sheets"])
        if screener_financials["cash_flows"]:
            await upsert_cash_flows(session, cid, screener_financials["cash_flows"])

        status["income"] = await upsert_income_statements(
            session, cid, fetch_result.income_statements
        )
        status["bs"]     = await upsert_balance_sheets(
            session, cid, fetch_result.balance_sheets
        )
        status["cf"]     = await upsert_cash_flows(
            session, cid, fetch_result.cash_flows
        )
        status["ratios"] = await upsert_key_ratios(session, cid, ratios)

        # ── 5. Quarterly data (optional) ──────────────────────────────────
        if include_quarterly:
            q_result = fetcher.fetch_quarterly(nse_symbol, num_quarters=12)
            await upsert_income_statements(session, cid, q_result.income_statements)
            await upsert_balance_sheets(session, cid, q_result.balance_sheets)
            await upsert_cash_flows(session, cid, q_result.cash_flows)

        await session.commit()

    except Exception as exc:
        await session.rollback()
        status["status"] = "error"
        status["error"]  = f"{type(exc).__name__}: {exc}"
        logger.error("seed.company.error", symbol=nse_symbol, error=status["error"])

    return status


def _load_nifty500_csv() -> list[tuple[str, str, str]]:
    """
    Load the Nifty 500 constituent list from the bundled CSV.
    Returns list of (nse_symbol, isin, display_name).
    """
    csv_path = Path(__file__).parent / "data" / "nifty500.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Nifty 500 CSV not found at {csv_path}.\n"
            "Run: python scripts/fetch_nifty500.py --csv > scripts/data/nifty500.csv"
        )
    companies: list[tuple[str, str, str]] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sym = row.get("symbol", "").strip()
            if sym:
                companies.append((sym, row.get("isin", "").strip(), row.get("name", sym).strip()))
    return companies


async def _already_seeded_symbols(session: AsyncSession) -> set[str]:
    """Return NSE symbols that already have at least one key_ratio row."""
    result = await session.execute(
        select(Company.nse_symbol)
        .join(KeyRatio, KeyRatio.company_id == Company.id)
        .distinct()
    )
    return {row[0] for row in result if row[0]}


async def _already_quarterly_seeded_symbols(session: AsyncSession) -> set[str]:
    """Return NSE symbols that already have at least one quarterly income_statement row."""
    result = await session.execute(
        select(Company.nse_symbol)
        .join(IncomeStatement, IncomeStatement.company_id == Company.id)
        .where(IncomeStatement.period_type == "quarterly")
        .distinct()
    )
    return {row[0] for row in result if row[0]}


async def run_seed(
    symbols: list[str] | None,
    years: int,
    use_screener: bool,
    dry_run: bool,
    index: str = "nifty50",
    skip_existing: bool = False,
    quarterly: bool = False,
) -> None:
    """Orchestrate seeding for all (or selected) companies."""

    # ── Decide the master company list ────────────────────────────────────
    if index == "nifty500":
        master = _load_nifty500_csv()       # (symbol, isin, name)
        master_tuples = [(s, i, n) for s, i, n in master]  # no BSE code in CSV
    else:
        master_tuples = list(NIFTY_50)      # (symbol, bse_code, name)

    # Filter company list
    if symbols:
        companies = [c for c in master_tuples if c[0] in {s.upper() for s in symbols}]
        not_found = {s.upper() for s in symbols} - {c[0] for c in companies}
        if not_found:
            logger.warning("seed.symbols_not_found", symbols=list(not_found))
    else:
        companies = master_tuples

    # ── Set up DB engine ──────────────────────────────────────────────────
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # ── Optionally skip already-seeded companies ───────────────────────────
    if skip_existing and not symbols:
        async with session_factory() as session:
            if quarterly:
                # When adding quarterly data, skip companies that already have it
                already_done = await _already_quarterly_seeded_symbols(session)
                skip_label = "quarterly-seeded"
            else:
                already_done = await _already_seeded_symbols(session)
                skip_label = "already-seeded"
        before = len(companies)
        companies = [c for c in companies if c[0] not in already_done]
        print(f"  Skipping {before - len(companies)} {skip_label} companies.")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Seeding {len(companies)} companies "
          f"(index={index}, {years}y, Screener={'yes' if use_screener else 'no'}, "
          f"skip_existing={skip_existing}, quarterly={quarterly})\n")

    results: list[dict[str, Any]] = []
    start = time.time()

    # When --quarterly --skip-existing: remaining companies have annual data
    # but no quarterly rows → use fast quarterly-only mode (no annual re-fetch)
    quarterly_only_mode = quarterly and skip_existing

    with tqdm(companies, unit="company", colour="cyan") as pbar:
        for nse_symbol, bse_code, display_name in pbar:
            pbar.set_description(f"{nse_symbol:<12}")

            async with session_factory() as session:
                status = await seed_company(
                    session=session,
                    nse_symbol=nse_symbol,
                    bse_code=bse_code,
                    display_name=display_name,
                    years=years,
                    use_screener=use_screener,
                    dry_run=dry_run,
                    include_quarterly=quarterly and not quarterly_only_mode,
                    quarterly_only=quarterly_only_mode,
                )
            results.append(status)

    await engine.dispose()

    # ── Summary table ──────────────────────────────────────────────────────
    elapsed = round(time.time() - start, 1)
    ok_count    = sum(1 for r in results if r["status"] in ("ok", "dry-run"))
    fail_count  = sum(1 for r in results if r["status"] not in ("ok", "dry-run"))

    print(f"\n\n{'─' * 80}")
    print(f"  Seed complete in {elapsed}s  |  "
          f"✓ {ok_count} succeeded  |  ✗ {fail_count} failed")
    print(f"{'─' * 80}\n")

    table = [
        [
            r["symbol"],
            r["name"][:30],
            r["income"],
            r["bs"],
            r["cf"],
            r["ratios"],
            f"{r['scrn_pl']}{'?' if r['scrn_err'] else ''}",
            r["status"],
            (r["error"][:40] if r["error"] else r.get("scrn_err", "")),
        ]
        for r in results
    ]
    print(tabulate(
        table,
        headers=["Symbol", "Name", "P&L", "BS", "CF", "Ratios", "Scrn P&L", "Status", "Error"],
        tablefmt="rounded_outline",
    ))

    if fail_count:
        print(f"\n⚠  {fail_count} companies failed. "
              "Re-run with --symbols <SYMBOL> to retry individual companies.\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the StockSage database with Nifty 50 / Nifty 500 financial data."
    )
    parser.add_argument(
        "--symbols", nargs="+", metavar="SYMBOL",
        help="Seed only these NSE symbols (e.g. --symbols TCS INFY RELIANCE)",
    )
    parser.add_argument(
        "--index", default="nifty50", choices=["nifty50", "nifty500"],
        help="Which index to seed: nifty50 (default) or nifty500",
    )
    parser.add_argument(
        "--years", type=int, default=5, metavar="N",
        help="Number of annual periods to fetch (default: 5, max: 10)",
    )
    parser.add_argument(
        "--no-screener", action="store_true",
        help="Skip Screener.in scraping (faster, but no promoter holding)",
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="Skip companies that already have key_ratio data in the DB (safe to resume)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch data but do not write to the database",
    )
    parser.add_argument(
        "--quarterly", action="store_true",
        help="Also seed quarterly P&L, balance sheet, and cash flow (last 12 quarters)",
    )
    args = parser.parse_args()

    asyncio.run(run_seed(
        symbols=args.symbols,
        years=min(args.years, 10),
        use_screener=not args.no_screener,
        dry_run=args.dry_run,
        index=args.index,
        skip_existing=args.skip_existing,
        quarterly=args.quarterly,
    ))


if __name__ == "__main__":
    main()
