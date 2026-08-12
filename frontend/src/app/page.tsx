import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, BarChart3, Brain, Shield, TrendingUp, Zap } from "lucide-react";
import { SearchBar } from "@/components/layout/SearchBar";
import { LandingNavActions, LandingAuthRedirect } from "@/components/layout/AuthRedirect";

export const metadata: Metadata = { title: "Home" };

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      {/* Auto-redirect logged-in users to /dashboard */}
      <LandingAuthRedirect />
      {/* ── Navigation ─────────────────────────────────────────────────────── */}
      <nav className="border-b border-gray-100 dark:border-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-gray-900 dark:text-white">ValuePilotage</span>
          </div>
          <div className="flex items-center gap-4">
            <LandingNavActions />
          </div>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-50 dark:bg-brand-950 border border-brand-100 dark:border-brand-900 text-brand-700 dark:text-brand-300 text-xs font-medium mb-8">
          <Zap className="w-3 h-3" />
          AI-powered equity research for India
        </div>

        <h1 className="text-5xl sm:text-6xl font-bold text-gray-900 dark:text-white leading-tight tracking-tight max-w-4xl mx-auto">
          Understand businesses,{" "}
          <span className="text-brand-600">not just numbers</span>
        </h1>

        <p className="mt-6 text-xl text-gray-500 dark:text-gray-400 max-w-2xl mx-auto leading-relaxed">
          ValuePilotage transforms financial data into investor understanding.
          Get research-analyst quality insights on any NSE-listed company in seconds.
        </p>

        {/* ── Hero Search ── */}
        <div className="mt-10 max-w-xl mx-auto">
          <SearchBar size="large" />
        </div>

        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          {POPULAR_SYMBOLS.map((s) => (
            <Link
              key={s.symbol}
              href={`/company/${s.symbol}`}
              className="text-xs px-3 py-1.5 rounded-full border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 hover:border-brand-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
            >
              {s.symbol}
            </Link>
          ))}
        </div>

        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-lg font-semibold hover:opacity-90 transition-opacity"
          >
            Browse all companies
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/company/RELIANCE"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 border border-gray-200 dark:border-gray-800 text-gray-700 dark:text-gray-300 rounded-lg font-semibold hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
          >
            <BarChart3 className="w-4 h-4" />
            Try with Reliance Industries
          </Link>
        </div>
      </section>

      {/* ── Feature Grid ───────────────────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {FEATURES.map((feature) => (
            <Link
              key={feature.title}
              href={feature.href}
              className="p-6 rounded-xl border border-gray-100 dark:border-gray-900 hover:border-brand-300 dark:hover:border-brand-700 hover:shadow-sm transition-all group"
            >
              <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-900 flex items-center justify-center mb-4 group-hover:bg-brand-50 dark:group-hover:bg-brand-950 transition-colors">
                <feature.icon className="w-5 h-5 text-gray-700 dark:text-gray-300 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors" />
              </div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-2 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                {feature.title}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
                {feature.description}
              </p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

const POPULAR_SYMBOLS = [
  { symbol: "RELIANCE" },
  { symbol: "TCS" },
  { symbol: "HDFCBANK" },
  { symbol: "INFY" },
  { symbol: "WIPRO" },
  { symbol: "TATAMOTORS" },
  { symbol: "BAJFINANCE" },
  { symbol: "ASIANPAINT" },
];

const FEATURES = [
  {
    icon: Brain,
    title: "AI Executive Summary",
    href: "/company/RELIANCE/research",
    description:
      "Understand a company's business model, competitive moat, and investment case in 60 seconds — written like a research analyst, not a data dump.",
  },
  {
    icon: BarChart3,
    title: "Quality Score Card",
    href: "/company/RELIANCE/quality",
    description:
      "5-dimension quality score: Business Quality, Financial Health, Management, Growth, and Valuation — each with a plain-English explanation.",
  },
  {
    icon: Shield,
    title: "Red Flag Detector",
    href: "/company/RELIANCE/risks",
    description:
      "AI-powered forensic analysis that flags accounting irregularities, governance issues, and financial stress before they become problems.",
  },
  {
    icon: TrendingUp,
    title: "10-Year Financial Trends",
    href: "/company/RELIANCE/financials",
    description:
      "P&L, Balance Sheet, and Cash Flow with AI commentary explaining what the numbers mean for the business — not just what they are.",
  },
  {
    icon: Zap,
    title: "Quarterly Results Analysis",
    href: "/company/RELIANCE/research",
    description:
      "Instant AI analysis every time quarterly results drop. Understand what changed, what management said, and what to watch next quarter.",
  },
  {
    icon: ArrowRight,
    title: "Peer Comparison",
    href: "/company/RELIANCE/peers",
    description:
      "Side-by-side comparison with peers, with AI explaining why one company trades at a premium or discount to the other.",
  },
];
