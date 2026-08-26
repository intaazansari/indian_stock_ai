# Software Design Document (SDD)
## ValuePilotage — Indian Stock AI Platform

**Version:** 1.0  
**Date:** August 2026  
**Repository:** https://github.com/intaazansari/indian_stock_ai

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Component Responsibilities](#3-component-responsibilities)
4. [Data Models](#4-data-models)
5. [Sequence Diagrams](#5-sequence-diagrams)
   - 5.1 Application Startup & Health Check
   - 5.2 User Registration & Login (JWT Auth)
   - 5.3 Home Page — Company Search
   - 5.4 Company Page Load (Full Profile)
   - 5.5 Live Price & Price History (yfinance)
   - 5.6 AI Analysis — Cache Hit (Fast Path)
   - 5.7 AI Analysis — Cache Miss → LLM Stream (Slow Path)
   - 5.8 Screener — Filter Companies
   - 5.9 Watchlist — Add / Remove
   - 5.10 Daily Price Refresh (GitHub Actions → Neon)
   - 5.11 Weekly Holdings Refresh (GitHub Actions → Neon)
   - 5.12 Quarterly Financials Refresh (GitHub Actions → Neon)
   - 5.13 Keep-Backend-Warm Cron (GitHub Actions → Render)
   - 5.14 Backend Cold-Start & Banner Lifecycle (Vercel → Render)
6. [API Reference Summary](#6-api-reference-summary)
7. [Infrastructure & Deployment](#7-infrastructure--deployment)
8. [Error Handling Strategy](#8-error-handling-strategy)
9. [Security Design](#9-security-design)

---

## 1. System Overview

ValuePilotage is an AI-powered equity research platform for NSE-listed Indian companies.

| Concern | Solution |
|---------|----------|
| **Frontend** | Next.js 15 on **Vercel** (free, unlimited) |
| **Backend API** | FastAPI (Python) on **Render** free tier |
| **Database** | **Neon** PostgreSQL (serverless, free tier) |
| **Cache** | **Render Redis** (Valkey 8, free 25 MB) |
| **AI / LLM** | Groq API via OpenAI-compatible SDK + **LangGraph** agents |
| **Data Pipeline** | GitHub Actions cron jobs (ubuntu-latest VMs) |
| **Background Workers** | Celery (currently disabled — tasks run sync) |

---

## 2. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         INTERNET / USERS                             │
└─────────────────────────────┬────────────────────────────────────────┘
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────┐
│              VERCEL  (Frontend — Free)               │
│                                                      │
│   Next.js 15  (valuepilotage.com)                   │
│   ┌──────────────────────────────────────────────┐  │
│   │  Pages: Home / Company / Screener /          │  │
│   │         Watchlist / Login / Signup           │  │
│   │  Proxy rewrites:                             │  │
│   │    /api/*   → Render backend /api/*          │  │
│   │    /health  → Render backend /health         │  │
│   └──────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │ Server-side proxy (no CORS)
                       ▼
┌─────────────────────────────────────────────────────┐
│            RENDER  (Backend — Free Tier)             │
│                                                      │
│   FastAPI  isa-backend-bpbt.onrender.com            │
│   ┌──────────────────────────────────────────────┐  │
│   │  Middleware: CORS, RateLimit, ReqLogging     │  │
│   │  Routers: auth / companies / financials /    │  │
│   │           analysis / search / screener /     │  │
│   │           watchlist / portfolio / market     │  │
│   │  Services: AuthService / CompanyService /    │  │
│   │            AnalysisService / FinancialService│  │
│   │  Agents (LangGraph):                         │  │
│   │    SupervisorAgent → ResearchAgent           │  │
│   │                    → FinancialAnalysisAgent  │  │
│   │                    → BusinessQualityAgent    │  │
│   │                    → ValuationAgent          │  │
│   │                    → RiskAgent               │  │
│   │                    → ManagementAgent         │  │
│   │                    → QuarterlyResultsAgent   │  │
│   │                    → ExecutiveSummaryAgent   │  │
│   └──────────────────────────────────────────────┘  │
│                        │             │               │
│               asyncpg  │    redis    │               │
└────────────────────────┼─────────────┼───────────────┘
                         │             │
          ┌──────────────┘             └─────────────┐
          ▼                                          ▼
┌──────────────────────┐            ┌───────────────────────┐
│   NEON  (Postgres)    │            │  RENDER Redis (Valkey) │
│   Serverless DB       │            │  25 MB free cache      │
│   Tables:             │            │  TTL-based analysis    │
│    companies          │            │  cache + rate limiting │
│    income_statements  │            └───────────────────────┘
│    balance_sheets     │
│    cash_flows         │
│    key_ratios         │
│    analysis_cache     │
│    users              │
│    watchlists         │
│    portfolios         │
└──────────────────────┘
          ▲
          │ Direct DB connection (no backend involved)
┌─────────────────────────────────────────────────────┐
│         GITHUB ACTIONS  (Data Pipeline)              │
│                                                      │
│   daily-price-refresh.yml     (Mon–Fri 16:00 IST)   │
│   weekly-holdings-refresh.yml (Sunday  23:30 IST)   │
│   quarterly-financials.yml    (4× per year)         │
│   keep-backend-warm.yml       (every 14 min,        │
│                                06:00–02:00 IST)     │
└─────────────────────────────────────────────────────┘
          │
          ▼ GROQ API (LLM)
┌──────────────────────┐
│   GROQ               │
│   gpt-oss-120b model │
│   OpenAI-compatible  │
└──────────────────────┘
```

---

## 3. Component Responsibilities

### 3.1 Frontend (Next.js — Vercel)

| Component | File | Responsibility |
|-----------|------|----------------|
| `BackendWakeupBanner` | `providers/BackendWakeupBanner.tsx` | Polls `/health` every 10s; shows amber banner after 2 consecutive failures; auto-invalidates TanStack Query cache when backend recovers |
| `apiClient` | `lib/api/client.ts` | Axios instance with `/api/v1` base; injects JWT Bearer token; handles 401 → auto-refresh → redirect |
| `next.config.ts` | root | Proxy rewrites: `/api/*` and `/health` → Render backend (eliminates CORS) |
| Auth Store | `stores/` | Zustand store managing `access_token` / `refresh_token` in localStorage |
| Pages | `app/(dashboard)/` | Company page, Screener, Watchlist, Portfolio |

### 3.2 Backend (FastAPI — Render)

| Layer | Responsibility |
|-------|---------------|
| **Middleware** | `RateLimitMiddleware` (IP-level), `RequestLoggingMiddleware` (structlog + request_id), `CORSMiddleware` |
| **Routers** | Route dispatching for 9 endpoint modules |
| **Endpoints** | Thin HTTP handlers — validate input, call service, return response |
| **Services** | Business logic: `AnalysisService`, `AuthService`, `CompanyService`, `FinancialService` |
| **Repositories** | Data access layer: `CompanyRepository`, `FinancialRepository`, `UserRepository` |
| **Agents** | `SupervisorAgent` (LangGraph) routes to 8 specialized sub-agents |
| **Models** | SQLAlchemy ORM: `Company`, `IncomeStatement`, `BalanceSheet`, `CashFlow`, `KeyRatio`, `AnalysisCache`, `User`, `Watchlist` |

### 3.3 Data Pipeline (GitHub Actions)

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `daily-price-refresh` | Mon–Fri 16:00 IST | yfinance `fast_info` → updates CMP, market cap, 52W H/L |
| `weekly-holdings-refresh` | Sunday 23:30 IST | Screener.in scrape → updates promoter/FII/DII % |
| `quarterly-financials` | Manual + 4 dates/year | Screener.in full scrape → P&L, BS, CF, Key Ratios |
| `keep-backend-warm` | Every 14 min (06:00–02:00 IST) | `curl /health` → prevents Render 15-min spin-down |

---

## 4. Data Models

```
┌────────────────────────────────────────────────────────────────────┐
│  companies                                                          │
│  id (UUID PK) | name | nse_symbol | bse_code | isin               │
│  sector | industry | market_cap_cr | cmp | week52_high/low         │
│  promoter_holding_pct | fii_holding_pct | dii_holding_pct          │
│  description | website | founded_year | headquarters               │
└───┬────────────────────────────────────────────────────────────────┘
    │ 1:N
    ├──► income_statements  (period_year, period_type, revenue_cr, pat_cr ...)
    ├──► balance_sheets     (period_year, period_type, total_assets_cr ...)
    ├──► cash_flows         (period_year, period_type, operating_cf_cr ...)
    ├──► key_ratios         (period_year, period_type, pe_ratio, pb_ratio,
    │                        roe_pct, roce_pct, debt_equity_ratio ...)
    ├──► analysis_cache     (agent_type, analysis_json, generated_at, ttl_hours)
    └──► watchlist_items    (user_id FK → users)

┌────────────────────────────────────────────────────────────────────┐
│  users                                                              │
│  id (UUID PK) | email (unique) | full_name | hashed_password       │
│  is_active | is_verified | created_at | updated_at                 │
└───┬────────────────────────────────────────────────────────────────┘
    │ 1:N
    └──► watchlists (id, user_id, company_id, created_at)
```

---

## 5. Sequence Diagrams

---

### 5.1 Application Startup & Health Check

```mermaid
sequenceDiagram
    participant Render as Render Platform
    participant App as FastAPI App
    participant DB as Neon PostgreSQL

    Render->>App: Container starts (entrypoint.sh)
    App->>DB: alembic upgrade head (run migrations)
    DB-->>App: Migrations applied ✓

    App->>App: create_application()
    Note over App: Add CORS, RateLimit,<br/>RequestLogging middleware
    Note over App: Register 9 routers under /api/v1

    App->>App: lifespan startup
    App->>DB: init_db() — create async pool
    DB-->>App: Pool ready ✓
    App->>App: Check QDRANT_URL (empty → skip)
    App->>App: Server ready on :8000

    Note over App: GitHub Actions pings every 14 min

    Render->>App: GET /health
    App->>DB: SELECT 1
    DB-->>App: OK
    App-->>Render: {"status":"healthy","db":"ok"} 200
```

---

### 5.2 User Registration & Login (JWT Auth)

```mermaid
sequenceDiagram
    participant Browser as Browser (Vercel)
    participant Next as Next.js (Vercel)
    participant API as FastAPI (Render)
    participant AuthSvc as AuthService
    participant DB as Neon PostgreSQL

    %% Registration
    Browser->>Next: POST /api/v1/auth/register
    Next->>API: POST /api/v1/auth/register (proxy)
    API->>AuthSvc: register(email, password, full_name)
    AuthSvc->>DB: SELECT user WHERE email = ?
    DB-->>AuthSvc: None (email free)
    AuthSvc->>AuthSvc: bcrypt.hash(password)
    AuthSvc->>DB: INSERT INTO users (...)
    DB-->>AuthSvc: User created
    AuthSvc-->>API: UserResponse
    API-->>Browser: 201 Created {id, email, full_name}

    %% Login
    Browser->>Next: POST /api/v1/auth/login
    Next->>API: POST /api/v1/auth/login (proxy)
    API->>AuthSvc: login(email, password)
    AuthSvc->>DB: SELECT user WHERE email = ?
    DB-->>AuthSvc: User row
    AuthSvc->>AuthSvc: verify_password(plain, hash)
    AuthSvc->>AuthSvc: create_access_token(user_id, exp=60min)
    AuthSvc->>AuthSvc: create_refresh_token(user_id, exp=30days)
    AuthSvc-->>API: TokenResponse
    API-->>Browser: 200 {access_token, refresh_token}
    Browser->>Browser: localStorage.setItem(access_token, refresh_token)
```

---

### 5.3 Home Page — Company Search

```mermaid
sequenceDiagram
    participant User as User
    participant Next as Next.js (Vercel)
    participant API as FastAPI (Render)
    participant CompSvc as CompanyService
    participant DB as Neon PostgreSQL

    User->>Next: Types "RELIANCE" in search bar
    Note over Next: Debounced 300ms

    Next->>API: GET /api/v1/search?q=RELIANCE&page=1&page_size=10
    API->>CompSvc: search(query="RELIANCE", params)
    CompSvc->>DB: SELECT companies WHERE name ILIKE '%RELIANCE%'<br/>OR nse_symbol ILIKE '%RELIANCE%'<br/>ORDER BY market_cap_cr DESC
    DB-->>CompSvc: [{id, name, nse_symbol, sector, cmp, market_cap_cr}...]
    CompSvc-->>API: PaginatedResponse[CompanySearchResult]
    API-->>Next: 200 {items:[...], total, page, total_pages}
    Next-->>User: Dropdown shows matching companies
```

---

### 5.4 Company Page Load (Full Profile)

```mermaid
sequenceDiagram
    participant User as User
    participant Next as Next.js (Vercel)
    participant API as FastAPI (Render)
    participant CompSvc as CompanyService
    participant DB as Neon PostgreSQL

    User->>Next: Navigate to /company/RELIANCE

    par Company profile
        Next->>API: GET /api/v1/companies/RELIANCE
        API->>CompSvc: get_by_symbol("RELIANCE")
        CompSvc->>DB: SELECT * FROM companies WHERE nse_symbol = 'RELIANCE'
        DB-->>CompSvc: Company row
        CompSvc-->>API: CompanyDetail
        API-->>Next: 200 CompanyDetail (name, sector, cmp, market_cap_cr,<br/>promoter_holding_pct, fii_pct, dii_pct, description)
    and Peer companies
        Next->>API: GET /api/v1/companies/RELIANCE/peers
        API->>CompSvc: get_peers("RELIANCE")
        CompSvc->>DB: SELECT peers in same industry ORDER BY market_cap_cr DESC
        DB-->>CompSvc: [PeerCompanyItem...]
        CompSvc-->>API: list[PeerCompanyItem]
        API-->>Next: 200 [peers list]
    and Financial data
        Next->>API: GET /api/v1/companies/RELIANCE/financials
        API->>DB: SELECT income_statements, key_ratios, balance_sheets, cash_flows
        DB-->>API: Financial rows
        API-->>Next: 200 financials JSON
    and Cached AI summary
        Next->>API: GET /api/v1/companies/RELIANCE/analysis/summary
        API-->>Next: 200 cached summary (or 404 if no cache yet)
    end

    Next-->>User: Render full company page
```

---

### 5.5 Live Price & Price History (yfinance)

```mermaid
sequenceDiagram
    participant Next as Next.js (Vercel)
    participant API as FastAPI (Render)
    participant Mem as In-Process Cache (dict)
    participant YF as Yahoo Finance API

    %% Live Price (60s TTL)
    Next->>API: GET /api/v1/companies/RELIANCE/live-price
    API->>Mem: Check _lp_cache["RELIANCE"] age < 60s?
    alt Cache hit
        Mem-->>API: Cached price data
        API-->>Next: 200 {cmp, change, change_pct, week52_high/low, market_cap_cr}
    else Cache miss
        API->>YF: yf.Ticker("RELIANCE.NS").fast_info
        YF-->>API: fast_info object
        API->>API: Compute change, change_pct, market_cap_cr (÷1e7 for Crores)
        API->>Mem: Store result with timestamp
        API-->>Next: 200 {cmp, change, change_pct, ...}
    end

    %% Price History (5 min TTL)
    Next->>API: GET /api/v1/companies/RELIANCE/price-history?period=1y
    API->>Mem: Check _ph_cache["RELIANCE:1y"] age < 300s?
    alt Cache hit
        Mem-->>API: Cached OHLCV list
    else Cache miss
        API->>YF: yf.Ticker("RELIANCE.NS").history(period="1y", interval="1d")
        YF-->>API: DataFrame (OHLCV rows)
        API->>API: Convert to [{date, open, high, low, close, volume}...]
        API->>Mem: Store with timestamp
    end
    API-->>Next: 200 [{date, open, high, low, close, volume}...]
```

---

### 5.6 AI Analysis — Cache Hit (Fast Path)

```mermaid
sequenceDiagram
    participant Next as Next.js (Vercel)
    participant API as FastAPI (Render)
    participant AnSvc as AnalysisService
    participant Redis as Redis (Render)
    participant DB as Neon PostgreSQL

    Next->>API: GET /api/v1/companies/RELIANCE/analysis/financial
    API->>AnSvc: get_analysis(company_id, agent_type="financial")

    AnSvc->>Redis: GET analysis_cache::{company_id}::financial
    alt Redis hit (TTL 24h)
        Redis-->>AnSvc: Cached JSON
        AnSvc-->>API: analysis dict
        API-->>Next: 200 {analysis JSON} ⚡ Fast
    else Redis miss
        Redis-->>AnSvc: nil
        AnSvc->>DB: SELECT FROM analysis_cache WHERE<br/>company_id=? AND agent_type='financial'
        alt DB cache hit (not stale)
            DB-->>AnSvc: AnalysisCache row
            AnSvc->>Redis: SETEX key 86400 {json} (repopulate Redis)
            AnSvc-->>API: analysis dict
            API-->>Next: 200 {analysis JSON}
        else No cache at all
            DB-->>AnSvc: None
            AnSvc-->>API: raise HTTP 404
            API-->>Next: 404 "No cached analysis"
            Note over Next: Shows "Generate Analysis" button
        end
    end
```

---

### 5.7 AI Analysis — Cache Miss → LLM Stream (Slow Path)

```mermaid
sequenceDiagram
    participant User as User
    participant Next as Next.js (Vercel)
    participant API as FastAPI (Render)
    participant AnSvc as AnalysisService
    participant Sup as SupervisorAgent (LangGraph)
    participant Sub as Specialized Sub-Agent
    participant Groq as Groq LLM API
    participant DB as Neon PostgreSQL
    participant Redis as Redis (Render)

    User->>Next: Clicks "Generate Analysis"
    Next->>API: POST /api/v1/companies/RELIANCE/analysis/stream<br/>{agent_type: "financial"}
    Note over API: Check AI rate limit (20 req/hour/user)

    API->>AnSvc: stream_analysis(company_id, "financial")
    AnSvc->>DB: SELECT company (name, sector, cmp, market_cap_cr,<br/>promoter/fii/dii holdings...)
    DB-->>AnSvc: Company context

    AnSvc->>DB: SELECT KeyRatios (last 3yr annual)
    AnSvc->>DB: SELECT BalanceSheet (latest annual)
    AnSvc->>DB: SELECT CashFlow (latest annual)
    AnSvc->>DB: SELECT IncomeStatement (last 6 rows for CAGR)
    DB-->>AnSvc: Financial context dict

    AnSvc->>Sup: agent.analyze({company_data, financial_context, agent_type})
    Sup->>Sup: LangGraph StateGraph._route_node()
    Sup->>Sup: _router() → "financial" edge
    Sup->>Sub: FinancialAnalysisAgent.analyze(input)
    Sub->>Sub: Build prompt with financial context
    Sub->>Groq: POST /openai/v1/chat/completions (gpt-oss-120b)
    Groq-->>Sub: Structured analysis JSON
    Sub-->>Sup: result dict
    Sup-->>AnSvc: result dict

    AnSvc->>DB: INSERT INTO analysis_cache (agent_type, analysis_json)
    AnSvc->>DB: COMMIT (so GET requests find it immediately)
    AnSvc->>Redis: SETEX key 86400 {json}

    AnSvc-->>API: yield SSE: data: {"result": {...}}
    API-->>Next: SSE stream token
    API-->>Next: SSE stream: data: [DONE]
    Next-->>User: Analysis renders via EventSource

    Note over Next,Redis: Future GET /analysis/financial → Redis hit ⚡
```

---

### 5.8 Screener — Filter Companies

```mermaid
sequenceDiagram
    participant User as User
    participant Next as Next.js (Vercel)
    participant API as FastAPI (Render)
    participant DB as Neon PostgreSQL

    User->>Next: Opens Screener page
    Next->>API: GET /api/v1/screener/sectors
    API->>DB: SELECT DISTINCT sector FROM companies ORDER BY sector
    DB-->>API: ["Banking","FMCG","IT","Pharma"...]
    API-->>Next: 200 [sectors list]
    Next-->>User: Populates sector dropdown

    User->>Next: Sets: ROE > 15%, D/E < 1, sector = "IT", sort by market_cap
    Next->>API: POST /api/v1/screener/filter<br/>{roe_min:15, debt_equity_max:1, sector:"IT",<br/>sort_by:"market_cap", page:1, page_size:25}

    API->>DB: Subquery: MAX(period_year) per company (latest annual ratios)
    API->>DB: JOIN companies + key_ratios ON latest year
    API->>DB: WHERE roe_pct >= 15<br/>AND debt_equity_ratio <= 1<br/>AND sector = 'IT'
    API->>DB: SELECT COUNT(*) → total
    API->>DB: ORDER BY market_cap_cr DESC NULLS LAST
    API->>DB: OFFSET 0 LIMIT 25
    DB-->>API: [{name, nse_symbol, pe_ratio, roe_pct, market_cap_cr...}...]
    API-->>Next: 200 {items:[...], total, page, total_pages}
    Next-->>User: Renders sortable, filterable company table
```

---

### 5.9 Watchlist — Add / Remove

```mermaid
sequenceDiagram
    participant User as User (Authenticated)
    participant Next as Next.js (Vercel)
    participant API as FastAPI (Render)
    participant DB as Neon PostgreSQL

    User->>Next: Opens Watchlist page
    Next->>API: GET /api/v1/watchlist<br/>Authorization: Bearer {access_token}
    API->>API: Decode JWT → extract user_id
    API->>DB: SELECT watchlist JOIN companies WHERE user_id=?<br/>ORDER BY created_at DESC
    DB-->>API: [WatchlistItem...]
    API-->>Next: 200 [{nse_symbol, name, sector, cmp, market_cap_cr}...]
    Next-->>User: Renders watchlist

    User->>Next: Clicks ⭐ on INFY company page
    Next->>API: POST /api/v1/watchlist/{company_id}<br/>Authorization: Bearer {access_token}
    API->>DB: SELECT company WHERE id=? (verify exists)
    DB-->>API: Company ✓
    API->>DB: SELECT watchlist WHERE user_id=? AND company_id=?
    DB-->>API: None (not duplicate)
    API->>DB: INSERT INTO watchlists (user_id, company_id)
    DB-->>API: Committed
    API-->>Next: 201 {"message":"Added to watchlist"}
    Next-->>User: ⭐ filled, toast shown

    User->>Next: Clicks ⭐ again to remove
    Next->>API: DELETE /api/v1/watchlist/{company_id}
    API->>DB: DELETE FROM watchlists WHERE user_id=? AND company_id=?
    DB-->>API: Committed
    API-->>Next: 200 {"message":"Removed from watchlist"}
    Next-->>User: ⭐ unfilled
```

---

### 5.10 Daily Price Refresh (GitHub Actions → Neon)

```mermaid
sequenceDiagram
    participant GH as GitHub Scheduler
    participant VM as GitHub Actions VM (ubuntu-latest)
    participant YF as Yahoo Finance API
    participant DB as Neon PostgreSQL

    Note over GH: Mon–Fri 10:30 UTC (16:00 IST)<br/>30 min after NSE market close (15:30)

    GH->>VM: Trigger daily-price-refresh.yml
    VM->>VM: checkout + setup Python 3.13 + pip install
    VM->>DB: Connect via DATABASE_URL secret (asyncpg direct)
    VM->>DB: SELECT nse_symbol FROM companies

    loop For each NSE symbol (~50 companies, ~2–5 min total)
        VM->>YF: yf.Ticker("{symbol}.NS").fast_info
        YF-->>VM: {last_price, market_cap, year_high, year_low}
        VM->>DB: UPDATE companies SET<br/>cmp=?, market_cap_cr=?, week52_high=?, week52_low=?<br/>WHERE nse_symbol=?
    end

    VM->>DB: COMMIT
    VM-->>GH: Workflow complete ✓

    Note over VM,DB: Render backend NEVER involved.<br/>Direct GitHub VM → Neon connection.<br/>Zero Render hours consumed.
```

---

### 5.11 Weekly Holdings Refresh (GitHub Actions → Neon)

```mermaid
sequenceDiagram
    participant GH as GitHub Scheduler
    participant VM as GitHub Actions VM
    participant Scr as Screener.in
    participant DB as Neon PostgreSQL

    Note over GH: Sunday 18:00 UTC (23:30 IST)

    GH->>VM: Trigger weekly-holdings-refresh.yml
    VM->>VM: checkout + Python 3.13 + pip install
    VM->>DB: SELECT companies with key_ratios (fully seeded ~50 Nifty)

    loop For each company (rate-limited)
        VM->>Scr: GET screener.in/company/{symbol}/consolidated/
        Note over VM,Scr: BSE code fallback for LTIM/TATAMOTORS
        Scr-->>VM: HTML shareholding table
        VM->>VM: Parse: promoter%, FII%, DII%, public%
        VM->>DB: UPDATE companies SET<br/>promoter_holding_pct=?, fii_holding_pct=?,<br/>dii_holding_pct=?, public_holding_pct=?
    end

    VM->>DB: COMMIT
    VM-->>GH: Workflow complete ✓
```

---

### 5.12 Quarterly Financials Refresh (GitHub Actions → Neon)

```mermaid
sequenceDiagram
    participant Dev as Developer (or Cron)
    participant VM as GitHub Actions VM
    participant Scr as Screener.in
    participant DB as Neon PostgreSQL

    Note over Dev: Manual trigger after Q results<br/>OR auto: Aug 15 / Nov 15 / Feb 15 / May 15

    Dev->>VM: Trigger quarterly-financials-refresh.yml<br/>(index=nifty50, years=5)
    VM->>VM: checkout + Python 3.13 + pip install

    loop For each company in index (~50 nifty50 / ~500 nifty500)
        VM->>Scr: GET screener.in/company/{symbol}/consolidated/
        Scr-->>VM: P&L / Balance Sheet / Cash Flow / Key Ratios (5yr)
        VM->>VM: Parse all financial tables into structured rows
        VM->>DB: UPSERT income_statements (revenue_cr, pat_cr, ebitda_cr...)
        VM->>DB: UPSERT balance_sheets   (total_assets_cr, debt_cr...)
        VM->>DB: UPSERT cash_flows       (operating_cf_cr, capex_cr...)
        VM->>DB: UPSERT key_ratios       (pe_ratio, pb_ratio, roe_pct,<br/>roce_pct, debt_equity_ratio...)
        VM->>VM: Rate-limit delay between companies
    end

    VM->>DB: COMMIT all upserts
    VM-->>Dev: Summary: X companies updated, Y failed
```

---

### 5.13 Keep-Backend-Warm Cron

```mermaid
sequenceDiagram
    participant GH as GitHub Scheduler
    participant VM as GitHub Actions VM
    participant Render as Render Backend

    Note over GH: Every 14 min, 00:00–20:59 UTC<br/>(06:00–02:00 IST) 7 days/week

    GH->>VM: Trigger keep-backend-warm.yml
    VM->>Render: GET /health (--max-time 60s)

    alt Backend awake (normal case)
        Render-->>VM: 200 {"status":"healthy"}
        VM-->>GH: ✓ HTTP 200 logged
        Note over Render: 15-min idle timer RESET ✓
    else Backend was cold (after 02:00–06:00 IST sleep window)
        Note over Render: Render wakes container (~30–90s)
        Render-->>VM: 200 {"status":"healthy"}
        VM-->>GH: ✓ HTTP 200 (may be slow but succeeds)
    end

    Note over GH,Render: Sleep window 20:30–00:30 UTC saves 4 hrs/day<br/>Monthly: 20h × 30d = 600h used / 750h limit ✅<br/>Buffer: 150 hrs remaining
```

---

### 5.14 Backend Cold-Start & Banner Lifecycle

```mermaid
sequenceDiagram
    participant User as User
    participant Next as Next.js (Vercel)
    participant Banner as BackendWakeupBanner
    participant TQ as TanStack Query
    participant Render as Render Backend

    Note over Render: Backend asleep (idle > 15 min)

    User->>Next: Opens valuepilotage.com
    Next->>Banner: Mount component
    Banner->>TQ: useQuery(["__backend_health__"])
    TQ->>Next: GET /health (Next.js proxy)
    Next->>Render: GET /health (proxied request)

    Render-->>Next: Timeout / 503 (cold)
    Next-->>TQ: Failure #1

    Note over TQ: retry:1, retryDelay:5000ms

    TQ->>Next: Retry GET /health (after 5s)
    Next->>Render: GET /health (still starting)
    Render-->>Next: Timeout / error
    Next-->>TQ: Failure #2 (failureCount = 2)

    TQ-->>Banner: isError=true, failureCount >= FAILURE_THRESHOLD(2)
    Banner-->>User: 🟡 Amber banner appears:<br/>"Backend is starting up (Render free tier)..."

    Banner->>TQ: refetchInterval = 10s (polling begins)

    Note over Render: ~30–90s — container fully awake

    TQ->>Next: Poll GET /health
    Next->>Render: GET /health
    Render-->>Next: 200 {"status":"healthy"}
    Next-->>TQ: isSuccess = true

    TQ-->>Banner: wasDownRef=true + isSuccess → invalidate all queries
    Banner->>TQ: queryClient.invalidateQueries() (all except health key)
    Banner-->>User: 🟢 Banner hides automatically

    TQ->>Next: Re-fetch company / financial / analysis queries
    Next->>Render: All API calls fire
    Render-->>Next: 200 responses
    Next-->>User: Page data loads automatically ✓
```

---

## 6. API Reference Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/register` | ❌ | Register new user |
| POST | `/api/v1/auth/login` | ❌ | Login → JWT tokens |
| POST | `/api/v1/auth/refresh` | ❌ | Refresh access token |
| GET | `/api/v1/auth/me` | ✅ JWT | Get current user profile |
| PATCH | `/api/v1/auth/me` | ✅ JWT | Update profile |
| POST | `/api/v1/auth/me/change-password` | ✅ JWT | Change password |
| GET | `/api/v1/companies/{symbol}` | ❌ | Full company profile |
| GET | `/api/v1/companies/{symbol}/peers` | ❌ | Peer companies |
| GET | `/api/v1/companies/{symbol}/price-history?period=` | ❌ | OHLCV history (yfinance, 5min cache) |
| GET | `/api/v1/companies/{symbol}/live-price` | ❌ | Live CMP + stats (60s cache) |
| GET | `/api/v1/companies/{symbol}/analysis/{agent_type}` | ❌ | Cached AI analysis |
| POST | `/api/v1/companies/{symbol}/analysis/stream` | ⚠️ Rate-limited | Fresh AI analysis via SSE |
| GET | `/api/v1/search?q=&page=&page_size=` | ❌ | Search companies |
| GET | `/api/v1/screener/sectors` | ❌ | List sectors for dropdown |
| POST | `/api/v1/screener/filter` | ❌ | Screen companies by financial criteria |
| GET | `/api/v1/watchlist` | ✅ JWT | User's watchlist |
| POST | `/api/v1/watchlist/{company_id}` | ✅ JWT | Add to watchlist |
| DELETE | `/api/v1/watchlist/{company_id}` | ✅ JWT | Remove from watchlist |
| GET | `/health` | ❌ | Health check (pings Neon DB) |

### AI Agent Types

| `agent_type` | Description |
|--------------|-------------|
| `research` | Business overview, moat, competitive position |
| `financial` | Revenue/PAT trends, margins, ROCE, ROE |
| `quality` | Business quality score, consistency |
| `valuation` | PE, PB, EV/EBITDA vs peers, fair value |
| `risk` | Key risk factors, debt, regulatory exposure |
| `management` | Management quality, promoter track record |
| `quarterly` | Latest quarter highlights, YoY/QoQ |
| `summary` | Executive summary combining all dimensions |

---

## 7. Infrastructure & Deployment

```
DEPLOYMENT PIPELINE
═══════════════════
Developer push to GitHub master
        │
        ├──► Vercel (auto-deploy frontend)
        │    - Build: next build (Vercel native, no Docker)
        │    - Env:   NEXT_PUBLIC_API_URL in Vercel dashboard
        │             → https://isa-backend-bpbt.onrender.com
        │
        └──► Render (auto-deploy backend via render.yaml)
             - Build: Docker (infrastructure/docker/backend.Dockerfile)
             - Context: ./backend
             - Entrypoint: entrypoint.sh
               1. alembic upgrade head   ← DB migrations first
               2. uvicorn app.main:app --host 0.0.0.0 --workers 2

RESOURCE PLAN (September 2026+)
════════════════════════════════
Service          Platform    Cost    Notes
───────────────────────────────────────────────────────
isa-backend      Render      Free    750 hr/month shared
isa-redis        Render      Free    Valkey 8, 25MB — no instance hours
Neon DB          Neon        Free    0.5GB storage, serverless compute
Frontend         Vercel      Free    Unlimited deployments
Data Pipeline    GitHub      Free    Actions 2000 min/month
Groq LLM         Groq        PAYG    Only on cache miss

RENDER HOUR BUDGET (September)
═══════════════════════════════
Backend awake:  20 hrs/day × 30 days = 600 hrs ✅
Sleep window:   02:00–06:00 IST (4 hrs off daily)
Buffer:         150 hrs remaining from 750hr limit
```

---

## 8. Error Handling Strategy

| Layer | Strategy |
|-------|----------|
| **Frontend network** | `parseApiError()` in `client.ts` — network errors → "starting up" message; HTTP errors → show `detail` from API |
| **Banner** | Shows only after 2 confirmed failures (`FAILURE_THRESHOLD=2`); retry once before confirming; auto-hides + re-fetches on recovery |
| **FastAPI global** | `ApplicationError` handler → JSON `{detail:"..."}` with correct HTTP status |
| **AnalysisService** | Redis unavailable is non-fatal — logs warning, falls back to PostgreSQL cache |
| **Health endpoint** | DB failure → `db:"warming_up"` but still returns HTTP 200 (Neon cold start expected, not a crash) |
| **Data pipeline** | Per-company try/except — one failed company never stops the batch; summary printed at end |
| **LangGraph agents** | SupervisorAgent catches agent errors; propagated as HTTP 500 |

---

## 9. Security Design

| Concern | Implementation |
|---------|---------------|
| **Authentication** | JWT HS256, `ACCESS_TOKEN_EXPIRE_MINUTES=60`, `REFRESH_TOKEN_EXPIRE_DAYS=30` |
| **Password storage** | bcrypt hash — plain password never stored or logged anywhere |
| **Token auto-refresh** | `client.ts` interceptor: 401 → refresh → retry; failure → clear tokens → `/login` |
| **CORS** | Tightly scoped to `valuepilotage.com`, `www.valuepilotage.com`, `isa-frontend.onrender.com`, `localhost:3000` only |
| **Rate limiting** | General: 60 req/min/IP (middleware); AI endpoints: 20 req/hour/user (dependency) |
| **Secrets** | All via Render / Vercel / GitHub environment variables — nothing in code |
| **DB URL** | `fix_database_url` validator auto-converts `postgresql://` → `postgresql+asyncpg://` and `sslmode` → `ssl` param |
| **DEBUG enforcement** | `model_validator` raises `ValueError` if `DEBUG=True` in production environment |
| **API docs** | `/api/docs` and `/api/redoc` only when `DEBUG=True` — disabled in production |
| **Allowed hosts** | `ALLOWED_HOSTS=["isa-backend-bpbt.onrender.com","localhost","127.0.0.1"]` |
| **SECRET_KEY** | Must be ≥ 32 chars (validated at startup); auto-generated by Render on first deploy |
