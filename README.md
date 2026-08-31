# ValuePilotage — Indian Stock AI Platform

> **AI-powered equity research platform for Indian markets.** Understand businesses, not just numbers.

[![CI](https://github.com/intaazansari/indian_stock_ai/actions/workflows/ci.yml/badge.svg)](https://github.com/intaazansari/indian_stock_ai/actions/workflows/ci.yml)

---

## Vision

ValuePilotage transforms raw financial data into investor understanding.  
It answers the questions that matter — Is this business good? Is management trustworthy?  
Is valuation attractive? What are the biggest risks? — instantly, at research-analyst quality.

---

## Features (MVP)

### Company Analysis
- **Overview** — sector, market cap, CMP, P/E, P/B, ROCE, ROE
- **AI Deep Analysis** — 8-agent LangGraph pipeline (Research, Financial, Quality, Valuation, Risk, Management, Quarterly, Summary)
- **Financials tab** — P&L, Balance Sheet, Cash Flow (annual + quarterly toggle), Key Ratios
- **Peer Comparison** — side-by-side ratio comparison with sector peers

### Portfolio & Watchlist
- Portfolio tracker with holdings, cost, current value, P&L
- Watchlist with quick-view metrics

### Discovery
- Full-text + fuzzy company search
- Stock screener (filter by P/E, ROCE, market cap, sector)

### Data Pipeline
- Auto-seed Nifty 50 / Nifty 500 fundamentals via Screener.in + yfinance
- Daily CMP + market cap refresh (GitHub Actions, Mon–Fri 16:00 IST)
- Weekly shareholding refresh (GitHub Actions, Sunday 23:30 IST)
- Quarterly financials refresh (GitHub Actions, 4× per year)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Presentation Layer       Next.js 15 (App Router) — Vercel          │
├─────────────────────────────────────────────────────────────────────┤
│  Application Layer        FastAPI  (REST + SSE streaming) — Render  │
├─────────────────────────────────────────────────────────────────────┤
│  Business Logic           Services (Company, Financial, Analysis)   │
├─────────────────────────────────────────────────────────────────────┤
│  AI Layer                 LangGraph Multi-Agent System              │
│                           Supervisor → [Research | Financial |      │
│                           Quality | Valuation | Risk | Management | │
│                           Quarterly | Summary]                      │
├─────────────────────────────────────────────────────────────────────┤
│  Data Access              SQLAlchemy async (PostgreSQL), Redis      │
├─────────────────────────────────────────────────────────────────────┤
│  Infrastructure           Neon (Postgres) · Render Redis            │
│                           GitHub Actions (data pipeline + warm-up)  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, Tailwind CSS v3, shadcn/ui, TanStack Query v5, Zustand v5 |
| Backend | Python 3.13, FastAPI 0.115, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Database | **Neon** PostgreSQL (serverless) |
| Cache | **Render Redis** / Valkey 8 (optional — falls back gracefully if empty) |
| Vector DB | Qdrant (optional — disabled by default, only for RAG features) |
| AI | LangGraph, OpenAI SDK → **Groq** (openai/gpt-oss-120b) |
| Task Queue | Celery (optional — disabled by default) |
| Deployment | **Frontend:** Vercel · **Backend:** Render free tier |

---

## Project Structure

```
indian_stock_ai/
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── agents/        # LangGraph multi-agent system
│   │   ├── api/v1/        # REST API endpoints
│   │   ├── core/          # Config, security, middleware
│   │   ├── db/            # Database session, base models
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── repositories/  # Data access layer
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   ├── services/      # Business logic
│   │   ├── vector_store/  # Qdrant integration (optional)
│   │   └── workers/       # Celery tasks (optional)
│   ├── alembic/           # Database migrations
│   ├── scripts/           # Seed + refresh scripts
│   └── tests/
├── frontend/              # Next.js application
│   └── src/
│       ├── app/           # App Router pages
│       ├── components/    # React components
│       ├── hooks/         # Custom React hooks
│       ├── lib/           # API clients, utilities
│       ├── stores/        # Zustand stores
│       └── types/         # TypeScript types
├── .github/workflows/     # CI + data pipeline + backend warm-up crons
├── docs/
│   └── SDD.md             # Software Design Document (full architecture + sequence diagrams)
├── infrastructure/
│   ├── docker/            # Dockerfiles
│   └── nginx/             # Nginx config
├── render.yaml            # Render infrastructure as code
└── docker-compose.yml
```

---

## Getting Started (Local Dev — No Docker)

### Prerequisites

- **Python 3.13+** — https://python.org/downloads
- **Node.js 22 LTS+** — https://nodejs.org (includes npm)
- **Git**
- **Neon account** (free) — https://neon.tech — for the database
- **Groq API key** (free) — https://console.groq.com

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/intaazansari/indian_stock_ai.git
cd indian_stock_ai
```

---

### Step 2 — Backend setup

```powershell
cd backend

# Create venv with Python 3.13 explicitly (important if you have multiple Python versions)
py -3.13 -m venv venv

# Activate venv
.\venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate         # macOS / Linux

# Upgrade pip then install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 3 — Backend environment file

```powershell
# Still in backend/ folder
Copy-Item ..\.env.example .env      # Windows PowerShell
# cp ../.env.example .env          # macOS / Linux
```

Open `backend/.env` and fill in these **2 required values**:

```env
# Neon DB → dashboard.neon.tech → your project → Connection Details → Connection string
# Paste the full string as-is — sslmode and channel_binding are stripped automatically
DATABASE_URL="postgresql://user:password@ep-xxx.neon.tech/neondb?sslmode=require&channel_binding=require"

# Groq API key → console.groq.com → API Keys
OPENAI_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxx"
```

Everything else (Redis, Celery, Qdrant) is pre-set to empty/disabled for local dev.

---

### Step 4 — Run database migrations

```powershell
# From backend/ with venv active
python -m alembic upgrade head
```

---

### Step 5 — Start the backend

```powershell
# From backend/ with venv active
python -m uvicorn app.main:app --reload --port 8000
```

✅ Backend running at **http://localhost:8000**  
✅ API docs at **http://localhost:8000/api/docs**

---

### Step 6 — Frontend setup (new terminal)

```powershell
cd frontend

# Create env file
Copy-Item .env.local.example .env.local   # Windows PowerShell
# cp .env.local.example .env.local        # macOS / Linux

# Install dependencies
npm install

# Start dev server
npm run dev
```

✅ Frontend running at **http://localhost:3000**

---

### Step 7 — Seed the database (optional but recommended)

```powershell
# From backend/ with venv active
python -m scripts.seed_db --index nifty50          # ~50 companies, ~5 min
python -m scripts.seed_db --index nifty500         # ~500 companies, ~30 min
```

---

## Docker (Alternative — Full Stack)

```bash
# From project root
docker-compose up -d
docker-compose exec backend alembic upgrade head
docker-compose exec backend python -m scripts.seed_db --index nifty50
```

---

## Development Commands

```bash
# Backend — run tests (from backend/ with venv active)
pytest tests/ -v

# Backend — create new migration
python -m alembic revision --autogenerate -m "description"

# Backend — apply migrations
python -m alembic upgrade head

# Backend — daily price refresh manually
python -m scripts.refresh_prices

# Frontend — lint
cd frontend && npm run lint

# Frontend — type check
cd frontend && npm run type-check

# Frontend — build for production
cd frontend && npm run build
```

---

## AI Agent System

Each agent has **one responsibility** and a **defined output schema**.

| Agent | Responsibility |
|---|---|
| `SupervisorAgent` | Routes to the right sub-agent via LangGraph |
| `ResearchAgent` | Business overview, model, competitive moat |
| `FinancialAnalysisAgent` | P&L trends, balance sheet health, cash flows |
| `BusinessQualityAgent` | ROCE, capital efficiency, business quality score |
| `ValuationAgent` | PE, PB, EV/EBITDA, fair value commentary |
| `RiskAgent` | Red flags, business risks, financial risks |
| `ManagementAgent` | Promoter quality, governance, salary benchmarks |
| `QuarterlyResultsAgent` | Quarter-on-quarter analysis, trend changes |
| `ExecutiveSummaryAgent` | Synthesises all agents into an investor brief |

---

## Data Pipeline (GitHub Actions — Runs automatically)

| Workflow | Schedule | What it does |
|---|---|---|
| `daily-price-refresh` | Mon–Fri 16:00 IST | yfinance → CMP, market cap, 52W H/L |
| `weekly-holdings-refresh` | Sunday 23:30 IST | Screener.in → promoter/FII/DII % |
| `quarterly-financials` | Manual + 4×/year | Full P&L, BS, CF, Key Ratios |
| `keep-backend-warm` | Every 14 min (06:00–02:00 IST) | Prevents Render free tier spin-down |

> All data pipeline workflows connect **directly to Neon DB** — Render backend is not involved and consumes zero Render hours.

---

## Deployment

| Service | Platform | Plan |
|---|---|---|
| Frontend | Vercel | Free (unlimited) |
| Backend API | Render | Free (750 hr/month) |
| Database | Neon | Free serverless |
| Redis cache | Render | Free (25 MB Valkey) |

See [docs/SDD.md](docs/SDD.md) for full architecture, sequence diagrams, and API reference.

---

## Roadmap

| Feature | Priority | Status |
|---|---|---|
| Interactive price chart (TradingView widget) | High | Planned |
| Market dashboard (Sensex, Nifty, gainers/losers) | High | Planned |
| Company comparison tool (side-by-side 3 stocks) | Medium | Planned |
| Earnings concall AI summaries (RAG) | Medium | Planned |
| News feed (BSE announcements + RSS) | Medium | Planned |
| Annual report RAG deep-dive | Low | Planned |
| Email alerts (watchlist price + AI refresh) | Low | Planned |
| Mobile-responsive PWA | Low | Planned |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

> **AI-first equity research platform for Indian markets.** Understand businesses, not just data.

[![CI](https://github.com/intaazansari/indian_stock_ai/actions/workflows/ci.yml/badge.svg)](https://github.com/intaazansari/indian_stock_ai/actions/workflows/ci.yml)

---

## Vision

StockSage AI transforms raw financial data into investor understanding.  
It answers the questions that matter — Is this business good? Is management trustworthy?  
Is valuation attractive? What are the biggest risks? — instantly, at research-analyst quality.

---

## Features (MVP)

### Company Analysis
- **Overview** — sector, market cap, CMP, P/E, P/B, ROCE, ROE
- **AI Deep Analysis** — 9-agent LangGraph pipeline (Research, Financial, Quality, Valuation, Risk, Management, Quarterly, Summary)
- **Financials tab** — P&L, Balance Sheet, Cash Flow (annual + quarterly toggle), Key Ratios
- **Peer Comparison** — side-by-side ratio comparison with sector peers

### Portfolio & Watchlist
- Portfolio tracker with holdings, cost, current value, P&L
- Watchlist with quick-view metrics

### Discovery
- Full-text + fuzzy company search
- Stock screener (filter by P/E, ROCE, market cap, sector)

### Data Pipeline
- Auto-seed Nifty 50 / Nifty 500 fundamentals via yfinance
- Daily CMP + market cap refresh script
- Optional: Redis caching, Celery background workers

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Presentation Layer       Next.js 14 (App Router)                   │
├─────────────────────────────────────────────────────────────────────┤
│  Application Layer        FastAPI  (REST + SSE streaming)           │
├─────────────────────────────────────────────────────────────────────┤
│  Business Logic           Services (Company, Financial, Analysis)   │
├─────────────────────────────────────────────────────────────────────┤
│  AI Layer                 LangGraph Multi-Agent System              │
│                           Supervisor → [Research | Financial |      │
│                           Quality | Valuation | Risk | Mgmt |       │
│                           Quarterly | Summary | News | Industry]    │
├─────────────────────────────────────────────────────────────────────┤
│  Data Access              Repositories (PostgreSQL, Redis, Qdrant)  │
├─────────────────────────────────────────────────────────────────────┤
│  Infrastructure           Docker · PostgreSQL · Redis · Qdrant      │
│                           Celery · Celery Beat · Nginx              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, Tailwind CSS v3, shadcn/ui, TanStack Query v5, Zustand v5 |
| Backend | Python 3.13, FastAPI 0.115, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Database | PostgreSQL 16 |
| Cache | Redis 7 (optional) |
| Vector DB | Qdrant (optional — for RAG features) |
| AI | LangGraph, OpenAI SDK → Groq (openai/gpt-oss-120b) |
| Task Queue | Celery + Celery Beat (optional) |
| Deployment | Docker, Render.com |

---

## Project Structure

```
indian-stock-ai/
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── agents/        # LangGraph multi-agent system
│   │   ├── api/v1/        # REST API endpoints
│   │   ├── core/          # Config, security, middleware
│   │   ├── db/            # Database session, base models
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── repositories/  # Data access layer
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   ├── services/      # Business logic
│   │   ├── vector_store/  # Qdrant integration
│   │   └── workers/       # Celery tasks
│   └── tests/
├── frontend/              # Next.js application
│   └── src/
│       ├── app/           # App Router pages
│       ├── components/    # React components
│       ├── hooks/         # Custom React hooks
│       ├── lib/           # API clients, utilities
│       ├── stores/        # Zustand stores
│       └── types/         # TypeScript types
├── data_pipeline/         # Data ingestion service
│   ├── scrapers/          # NSE/BSE data scrapers
│   ├── parsers/           # Financial data parsers
│   └── processors/        # Data normalisation
├── infrastructure/
│   ├── docker/            # Dockerfiles
│   └── nginx/             # Nginx config
└── docker-compose.yml
```

---

## Getting Started

### Prerequisites

- Docker Desktop
- Node.js 20+
- Python 3.13+
- Groq API key (free at https://console.groq.com) — or any OpenAI-compatible endpoint

### 1. Clone & configure

```bash
git clone https://github.com/intaazansari/indian_stock_ai.git
cd indian_stock_ai
cp .env.example .env
# Edit .env — set DATABASE_URL, OPENAI_API_KEY (Groq key), SECRET_KEY
```

### 2a. Docker (full stack)

```bash
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

### 2b. Local dev (no Docker)

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

### 3. Seed the database

```bash
# From backend/ directory (venv active)
python -m scripts.seed_db --index nifty50
# For all 500 companies:
python -m scripts.seed_db --index nifty500
# Add quarterly financials:
python -m scripts.seed_db --index nifty500 --quarterly --skip-existing
```

### 4. Open the app

- **Frontend:** http://localhost:3000
- **API docs:** http://localhost:8000/api/docs (dev mode only)

---

## Development Commands

```bash
# Backend — run tests (from backend/ with venv active)
pytest tests/ -v

# Backend — create new migration
alembic revision --autogenerate -m "description"

# Backend — apply migrations
alembic upgrade head

# Backend — daily price refresh
python -m scripts.refresh_prices

# Frontend — run tests
cd frontend && npm test

# Frontend — type check
cd frontend && npm run type-check

# Frontend — lint
cd frontend && npm run lint
```

---

## AI Agent System

Each agent has **one responsibility** and a **defined output schema**.

| Agent | Responsibility |
|---|---|
| `SupervisorAgent` | Routes user queries to the right sub-agent |
| `ResearchAgent` | Business overview, model, competitive moat |
| `FinancialAnalysisAgent` | P&L trends, balance sheet health, cash flows |
| `BusinessQualityAgent` | ROCE, capital efficiency, business quality score |
| `ValuationAgent` | PE, PB, DCF, fair value estimate |
| `RiskAgent` | Red flags, business risks, financial risks |
| `ManagementAgent` | Promoter quality, governance, salary benchmarks |
| `QuarterlyResultsAgent` | Quarter-on-quarter analysis, trend changes |
| `AnnualReportAgent` | RAG-powered deep dive into annual reports |
| `NewsSentimentAgent` | News sentiment, event classification |
| `ExecutiveSummaryAgent` | Synthesises all agents into an investor brief |

---

## Roadmap

| Feature | Priority | Status |
|---|---|---|
| Shareholding pattern (Promoter / FII / DII %) | High | Planned |
| CAGR summary cards (3yr / 5yr Sales & Profit) | High | Planned |
| Interactive price chart (TradingView widget) | High | Planned |
| Market dashboard (Sensex, Nifty, gainers/losers) | Medium | Planned |
| Company comparison tool (side-by-side 3 stocks) | Medium | Planned |
| Earnings concall AI summaries (RAG) | Medium | Planned |
| News feed (BSE announcements + RSS) | Medium | Planned |
| Annual report RAG deep-dive | Low | Planned |
| Email alerts (watchlist price + AI refresh) | Low | Planned |
| Mobile-responsive PWA | Low | Planned |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
