"use client";

import Link from "next/link";
import { TrendingUp, TrendingDown } from "lucide-react";
import { useMarketMovers } from "@/hooks/useMarketMovers";
import { cn } from "@/lib/utils";
import type { MarketMover } from "@/lib/api/market";

function fmtPrice(value: string) {
  const n = parseFloat(value);
  return isNaN(n) ? "—" : `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function MoverRow({ mover, positive }: { mover: MarketMover; positive: boolean }) {
  const changePct = parseFloat(mover.change_pct);
  return (
    <Link
      href={`/company/${mover.symbol}`}
      className="flex items-center justify-between px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-900/30 transition-colors rounded-lg"
    >
      <div className="flex items-center gap-3 min-w-0">
        <span className="text-xs text-gray-400 dark:text-gray-500 w-4 shrink-0 tabular-nums">{mover.rank}</span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{mover.symbol}</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 truncate max-w-[160px]">{mover.company}</p>
        </div>
      </div>
      <div className="text-right shrink-0 pl-2">
        <p className="text-sm font-medium text-gray-900 dark:text-white tabular-nums">{fmtPrice(mover.close)}</p>
        <p className={cn(
          "text-xs font-medium tabular-nums",
          positive ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
        )}>
          {positive ? "+" : ""}{isNaN(changePct) ? "—" : changePct.toFixed(2)}%
        </p>
      </div>
    </Link>
  );
}

function MoversList({
  title,
  icon,
  movers,
  positive,
}: {
  title: string;
  icon: React.ReactNode;
  movers: MarketMover[];
  positive: boolean;
}) {
  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-900 flex items-center gap-2">
        {icon}
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
      </div>
      <div className="p-1.5">
        {movers.length === 0 ? (
          <p className="text-xs text-gray-400 py-6 text-center">No data yet for the latest trading day.</p>
        ) : (
          movers.map((m) => <MoverRow key={`${m.symbol}-${m.rank}`} mover={m} positive={positive} />)
        )}
      </div>
    </div>
  );
}

function SkeletonList() {
  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 p-4 space-y-3 animate-pulse">
      <div className="h-4 w-28 skeleton rounded mb-2" />
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-9 skeleton rounded" />
      ))}
    </div>
  );
}

export function TopMovers({ limit = 10 }: { limit?: number }) {
  const { data, isLoading } = useMarketMovers(limit);

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          Top Gainers &amp; Losers
        </h2>
        {data?.date && (
          <span className="text-xs text-gray-400 dark:text-gray-500">
            As of {new Date(data.date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {isLoading ? (
          <>
            <SkeletonList />
            <SkeletonList />
          </>
        ) : (
          <>
            <MoversList
              title="Top Gainers"
              icon={<TrendingUp className="w-4 h-4 text-emerald-500" />}
              movers={data?.gainers ?? []}
              positive
            />
            <MoversList
              title="Top Losers"
              icon={<TrendingDown className="w-4 h-4 text-red-500" />}
              movers={data?.losers ?? []}
              positive={false}
            />
          </>
        )}
      </div>
    </section>
  );
}
