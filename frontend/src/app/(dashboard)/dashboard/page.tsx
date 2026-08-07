import { MarketOverview } from "@/components/dashboard/MarketOverview";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Dashboard — ValuePilotage" };

export default function DashboardHomePage() {
  return (
    <div className="space-y-8">
      {/* ── Market Overview ──────────────────────────────────────────────── */}
      <MarketOverview />

      {/* ── Discovery Header ─────────────────────────────────────────────── */}
      <div className="text-center py-4">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Discover Indian businesses
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          Search any NSE or BSE listed company using the search bar above
        </p>
      </div>

      {/* ── Quick Access ─────────────────────────────────────────────────── */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Popular Companies
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {POPULAR_COMPANIES.map((c) => (
            <Link
              key={c.symbol}
              href={`/company/${c.symbol}`}
              className="flex flex-col items-center p-4 rounded-xl border border-gray-100 dark:border-gray-900 hover:border-gray-200 dark:hover:border-gray-800 hover:bg-white dark:hover:bg-gray-900 transition-all text-center"
            >
              <span className="text-xs font-bold text-brand-600 dark:text-brand-400 font-mono mb-1">
                {c.symbol}
              </span>
              <span className="text-xs text-gray-600 dark:text-gray-400 leading-tight">
                {c.name}
              </span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

const POPULAR_COMPANIES = [
  { symbol: "RELIANCE", name: "Reliance Industries" },
  { symbol: "TCS", name: "Tata Consultancy" },
  { symbol: "HDFCBANK", name: "HDFC Bank" },
  { symbol: "INFY", name: "Infosys" },
  { symbol: "HINDUNILVR", name: "Hindustan Unilever" },
  { symbol: "ICICIBANK", name: "ICICI Bank" },
  { symbol: "KOTAKBANK", name: "Kotak Mahindra Bank" },
  { symbol: "BAJFINANCE", name: "Bajaj Finance" },
  { symbol: "WIPRO", name: "Wipro" },
  { symbol: "ASIANPAINT", name: "Asian Paints" },
  { symbol: "TITAN", name: "Titan Company" },
  { symbol: "NESTLEIND", name: "Nestle India" },
];
