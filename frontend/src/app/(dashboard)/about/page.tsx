import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  Brain,
  Cloud,
  Database,
  Layers,
  Search,
  Server,
  Shield,
  Sparkles,
  Target,
  Workflow,
} from "lucide-react";

export const metadata: Metadata = {
  title: "About",
  description:
    "The story behind ValuePilotage — who built it, why, and how the AI-powered Indian equity research platform is engineered.",
};

export default function AboutPage() {
  return (
    <div className="space-y-8">
      {/* ── Founder ───────────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 p-6 sm:p-8">
        <div className="inline-flex w-fit items-center gap-2 px-3 py-1 rounded-full bg-brand-50 dark:bg-brand-950 border border-brand-100 dark:border-brand-900 text-brand-700 dark:text-brand-300 text-xs font-medium mb-5">
          <Sparkles className="w-3 h-3" />
          About ValuePilotage
        </div>
        <div className="flex items-center gap-4">
          <Image
            src="/about/imtiyaz.jpg"
            alt="Imtiyaz, creator of ValuePilotage"
            width={80}
            height={80}
            priority
            className="w-16 h-16 sm:w-20 sm:h-20 rounded-full object-cover ring-2 ring-brand-100 dark:ring-brand-900 shrink-0"
          />
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
              Hi, I&apos;m Imtiyaz
            </h1>
            <p className="mt-0.5 text-sm font-medium text-brand-600 dark:text-brand-400">
              Founder &amp; developer of ValuePilotage
            </p>
          </div>
        </div>
        <div className="mt-5 space-y-3 text-gray-600 dark:text-gray-400 leading-relaxed max-w-3xl">
          <p>
            I built ValuePilotage because researching an Indian company properly
            meant jumping between annual reports, exchange filings, screeners and
            spreadsheets — and still not getting a clear answer to the simple
            question: <em>is this a good business?</em>
          </p>
          <p>
            ValuePilotage brings that work into one place. It combines ten years of
            financial data with AI agents that read the numbers the way a research
            analyst would, and explain business quality, valuation and risk in plain
            English.
          </p>
        </div>
        <div className="mt-6">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            Explore companies
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── Principles ────────────────────────────────────────────────────── */}
      <section className="grid gap-4 md:grid-cols-3">
        {PRINCIPLES.map((p) => (
          <Card key={p.title}>
            <IconBadge icon={p.icon} />
            <h3 className="mt-3 font-semibold text-gray-900 dark:text-white">{p.title}</h3>
            <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
              {p.description}
            </p>
          </Card>
        ))}
      </section>

      {/* ── Architecture ──────────────────────────────────────────────────── */}
      <section>
        <SectionHeading
          title="How it's built"
          subtitle="A production-grade stack designed to run reliably on free and low-cost cloud tiers."
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {ARCHITECTURE.map((layer) => (
            <Card key={layer.title}>
              <div className="flex items-center gap-3">
                <IconBadge icon={layer.icon} />
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">{layer.title}</h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{layer.host}</p>
                </div>
              </div>
              <ul className="mt-4 space-y-1.5 text-sm text-gray-600 dark:text-gray-400">
                {layer.points.map((point) => (
                  <li key={point} className="flex gap-2">
                    <span className="mt-2 w-1 h-1 rounded-full bg-brand-500 shrink-0" />
                    {point}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      </section>

      {/* ── AI agents ─────────────────────────────────────────────────────── */}
      <section>
        <SectionHeading
          title="The AI research team"
          subtitle="A LangGraph supervisor routes each question to specialised agents, and results are cached so repeat visits load instantly."
        />
        <Card>
          <div className="flex flex-wrap items-center gap-2 pb-4 mb-4 border-b border-gray-100 dark:border-gray-900">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 text-white text-sm font-medium">
              <Workflow className="w-4 h-4" />
              Supervisor agent
            </span>
            <ArrowRight className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-500 dark:text-gray-400">
              delegates to 8 specialists
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {AGENTS.map((agent) => (
              <div key={agent.name} className="rounded-lg bg-gray-50 dark:bg-gray-900 px-3 py-2.5">
                <p className="text-sm font-medium text-gray-900 dark:text-white">{agent.name}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{agent.role}</p>
              </div>
            ))}
          </div>
        </Card>
      </section>

      {/* ── Disclaimer ────────────────────────────────────────────────────── */}
      <section className="rounded-xl border border-amber-200 dark:border-amber-900/50 bg-amber-50 dark:bg-amber-950/20 px-5 py-4">
        <div className="flex gap-3">
          <Shield className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <p className="text-sm text-amber-800 dark:text-amber-300 leading-relaxed">
            ValuePilotage is an educational research tool and is not a SEBI-registered
            investment adviser. Nothing on this site is investment advice — always do your
            own research before making investment decisions.
          </p>
        </div>
      </section>
    </div>
  );
}

// ── Building blocks ───────────────────────────────────────────────────────────

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 p-5">
      {children}
    </div>
  );
}

function IconBadge({ icon: Icon }: { icon: React.ElementType }) {
  return (
    <div className="w-10 h-10 rounded-lg bg-brand-50 dark:bg-brand-950 flex items-center justify-center shrink-0">
      <Icon className="w-5 h-5 text-brand-600 dark:text-brand-400" />
    </div>
  );
}

function SectionHeading({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">{title}</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>
    </div>
  );
}

// ── Content ───────────────────────────────────────────────────────────────────

const PRINCIPLES = [
  {
    icon: Target,
    title: "Understanding over data",
    description:
      "Numbers alone don't make an investment case. Every metric comes with an explanation of what it means for the business.",
  },
  {
    icon: Search,
    title: "Built for Indian markets",
    description:
      "Focused on NSE-listed companies, with Indian reporting conventions (₹ Crore), NSE trading holidays and local shareholding patterns.",
  },
  {
    icon: Shield,
    title: "Transparent and honest",
    description:
      "Red flags are surfaced as prominently as strengths, and AI output is always grounded in the underlying financial data.",
  },
];

const ARCHITECTURE = [
  {
    icon: Layers,
    title: "Frontend",
    host: "Next.js 15 · Vercel",
    points: [
      "React 19, TypeScript and Tailwind CSS",
      "TanStack Query for caching, Zustand for state",
      "Recharts price and financial-trend charts",
      "Server-side API proxy — no CORS exposure",
    ],
  },
  {
    icon: Server,
    title: "Backend API",
    host: "FastAPI · Render (Docker)",
    points: [
      "Async Python with SQLAlchemy 2.0 and asyncpg",
      "JWT authentication with refresh tokens",
      "Layered design: routers → services → repositories",
      "Structured JSON logging with request IDs",
    ],
  },
  {
    icon: Brain,
    title: "AI layer",
    host: "LangGraph · Groq",
    points: [
      "Supervisor + 8 specialised analysis agents",
      "Open-weight LLM via OpenAI-compatible API",
      "Streaming responses over Server-Sent Events",
      "Per-user rate limiting on fresh analyses",
    ],
  },
  {
    icon: Database,
    title: "Data & cache",
    host: "Neon PostgreSQL · Redis",
    points: [
      "Serverless Postgres with Alembic migrations",
      "10 years of P&L, balance sheet and cash flow",
      "Redis plus a database cache for AI analyses",
      "Daily top gainers / losers snapshots",
    ],
  },
  {
    icon: Workflow,
    title: "Data pipeline",
    host: "GitHub Actions",
    points: [
      "Daily price refresh after NSE close (16:00 IST)",
      "Weekly promoter / FII / DII holdings refresh",
      "Quarterly financial statement refresh",
      "Automatically skips NSE trading holidays",
    ],
  },
  {
    icon: Cloud,
    title: "Operations",
    host: "CI/CD · monitoring",
    points: [
      "Infrastructure as code with render.yaml",
      "Automatic deploys from GitHub on every push",
      "Health checks plus an uptime monitor",
      "Graceful cold-start handling in the UI",
    ],
  },
];

const AGENTS = [
  { name: "Research", role: "Business model, moat and competitive position" },
  { name: "Financial analysis", role: "Revenue and profit trends, margins, ROCE, ROE" },
  { name: "Business quality", role: "Consistency and quality scoring" },
  { name: "Valuation", role: "P/E, P/B, EV/EBITDA vs peers, fair value" },
  { name: "Risk", role: "Debt, governance and regulatory red flags" },
  { name: "Management", role: "Promoter track record and capital allocation" },
  { name: "Quarterly results", role: "Latest quarter, YoY and QoQ changes" },
  { name: "Executive summary", role: "One investment case combining every view" },
];
