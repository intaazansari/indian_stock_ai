"use client";

import { useCompany } from "@/hooks/useCompany";

const SEGMENTS = [
  {
    key:   "promoter_holding_pct" as const,
    label: "Promoter",
    bar:   "bg-indigo-500 dark:bg-indigo-400",
    text:  "text-indigo-600 dark:text-indigo-400",
    dot:   "bg-indigo-500 dark:bg-indigo-400",
  },
  {
    key:   "fii_holding_pct" as const,
    label: "FII",
    bar:   "bg-emerald-500 dark:bg-emerald-400",
    text:  "text-emerald-600 dark:text-emerald-400",
    dot:   "bg-emerald-500 dark:bg-emerald-400",
  },
  {
    key:   "dii_holding_pct" as const,
    label: "DII",
    bar:   "bg-amber-500 dark:bg-amber-400",
    text:  "text-amber-600 dark:text-amber-400",
    dot:   "bg-amber-500 dark:bg-amber-400",
  },
  {
    key:   "public_holding_pct" as const,
    label: "Public",
    bar:   "bg-gray-400 dark:bg-gray-500",
    text:  "text-gray-600 dark:text-gray-400",
    dot:   "bg-gray-400 dark:bg-gray-500",
  },
];

interface ShareholdingCardProps {
  symbol: string;
}

export function ShareholdingCard({ symbol }: ShareholdingCardProps) {
  const { data: company, isLoading } = useCompany(symbol);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-100 dark:border-gray-900 p-5 space-y-4">
        <div className="h-5 w-44 skeleton" />
        <div className="h-3 skeleton rounded-full" />
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-6 skeleton rounded" />
        ))}
      </div>
    );
  }

  if (!company) return null;

  // Check if any holding data exists
  const hasData = SEGMENTS.some((s) => company[s.key] != null);
  if (!hasData) return null;

  const segments = SEGMENTS.map((s) => ({
    ...s,
    pct: company[s.key] != null ? parseFloat(String(company[s.key])) : 0,
  }));

  // Total for the stacked bar (should sum to ~100, but may not due to rounding)
  const total = segments.reduce((acc, s) => acc + s.pct, 0) || 100;

  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-900 flex items-center justify-between">
        <div className="flex items-center gap-2 flex-wrap">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Shareholding Pattern</h2>
          <span className="text-xs font-mono font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950 px-1.5 py-0.5 rounded">
            {symbol}
          </span>
        </div>
      </div>

      <div className="px-5 pt-4 pb-5 space-y-4">
        {/* Stacked bar */}
        <div className="flex h-2.5 rounded-full overflow-hidden gap-px">
          {segments.map((s) =>
            s.pct > 0 ? (
              <div
                key={s.key}
                className={s.bar}
                style={{ width: `${(s.pct / total) * 100}%` }}
                title={`${s.label}: ${s.pct.toFixed(1)}%`}
              />
            ) : null
          )}
        </div>

        {/* Legend rows */}
        <div className="space-y-3">
          {segments.map((s) => (
            <div key={s.key} className="flex items-center justify-between gap-2">
              {/* Label */}
              <div className="flex items-center gap-2 min-w-0">
                <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${s.dot}`} />
                <span className="text-xs text-gray-600 dark:text-gray-400">{s.label}</span>
              </div>

              {/* Progress bar + value */}
              <div className="flex items-center gap-2">
                <div className="w-24 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${s.bar}`}
                    style={{ width: `${Math.min(100, s.pct)}%` }}
                  />
                </div>
                <span className={`text-xs font-semibold tabular-nums w-12 text-right ${s.pct > 0 ? s.text : "text-gray-300 dark:text-gray-600"}`}>
                  {s.pct > 0 ? `${s.pct.toFixed(1)}%` : "—"}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Total check */}
        {Math.abs(total - 100) > 1 && total > 0 && (
          <p className="text-[10px] text-gray-400 dark:text-gray-600">
            Total: {total.toFixed(1)}% (rounding)
          </p>
        )}
      </div>
    </div>
  );
}
