# StockSage AI — Indian Stock Fundamental Analysis Platform

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
