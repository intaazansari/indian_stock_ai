"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useMarketIndices } from "@/hooks/useMarketIndices";
import { cn } from "@/lib/utils";

function fmt(n: number | null, decimals = 2) {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: decimals, minimumFractionDigits: decimals });
}

function IndexCard({ index }: { index: { name: string; short: string; price: number | null; change: number | null; change_pct: number | null } }) {
  const up = (index.change ?? 0) >= 0;
  const neutral = index.change === null;

  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 px-5 py-4 flex flex-col gap-1 hover:border-gray-200 dark:hover:border-gray-800 transition-colors">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          {index.short}
        </span>
        {neutral ? (
          <Minus className="w-3.5 h-3.5 text-gray-400" />
        ) : up ? (
          <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
        ) : (
          <TrendingDown className="w-3.5 h-3.5 text-red-500" />
        )}
      </div>

      <span className="text-xl font-bold text-gray-900 dark:text-white tabular-nums">
        {fmt(index.price, 0)}
      </span>

      <div className={cn(
        "flex items-center gap-1.5 text-xs font-medium tabular-nums",
        neutral ? "text-gray-400" : up ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
      )}>
        <span>{up && !neutral ? "+" : ""}{fmt(index.change)}</span>
        <span className="text-gray-300 dark:text-gray-700">|</span>
        <span>{up && !neutral ? "+" : ""}{fmt(index.change_pct)}%</span>
      </div>

      <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{index.name}</p>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 px-5 py-4 animate-pulse">
      <div className="h-3 w-16 skeleton rounded mb-3" />
      <div className="h-6 w-28 skeleton rounded mb-2" />
      <div className="h-3 w-20 skeleton rounded mb-1" />
      <div className="h-3 w-14 skeleton rounded" />
    </div>
  );
}

export function MarketOverview() {
  const { data, isLoading } = useMarketIndices();

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          Market Overview
        </h2>
        <span className="text-xs text-gray-400 dark:text-gray-500">Live · refreshes every 60s</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)
          : data?.map((idx) => <IndexCard key={idx.symbol} index={idx} />)
        }
      </div>
    </section>
  );
}
