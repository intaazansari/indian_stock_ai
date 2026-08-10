"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { formatCr, formatNumber, formatPercent } from "@/lib/utils";

type PeriodType = "annual" | "quarterly";

interface IncomeItem {
  period_year: number;
  period_quarter: number | null;
  period_type: string;
  revenue_cr: string | null;
  ebitda_cr: string | null;
  pat_cr: string | null;
  eps_basic: string | null;
}

interface RatioItem {
  period_year: number;
  roe_pct: string | null;
  roce_pct: string | null;
  pe_ratio: string | null;
  pb_ratio: string | null;
  ebitda_margin_pct: string | null;
  net_profit_margin_pct: string | null;
  debt_equity_ratio: string | null;
}

interface FinancialSummary {
  income_statements: IncomeItem[];
  key_ratios: RatioItem[];
}

/** "Q2FY25" or "FY2025" depending on period type */
function periodLabel(item: IncomeItem): string {
  if (item.period_type === "quarterly" && item.period_quarter) {
    return `Q${item.period_quarter}FY${String(item.period_year).slice(2)}`;
  }
  return `FY${item.period_year}`;
}

function useFinancials(symbol: string, period: PeriodType) {
  const num = period === "quarterly" ? 12 : 5;
  return useQuery<FinancialSummary>({
    queryKey: ["financials", symbol, period],
    queryFn: async () => {
      const { data } = await apiClient.get(
        `/companies/${symbol}/financials?period_type=${period}&years=${num}`
      );
      return data;
    },
    staleTime: 10 * 60 * 1000,
    enabled: Boolean(symbol),
  });
}

function Row({ label, values }: { label: string; values: (string | number | null)[] }) {
  return (
    <tr className="border-b border-gray-50 dark:border-gray-900/50 hover:bg-gray-50 dark:hover:bg-gray-900/30">
      <td className="px-4 py-2.5 text-xs text-gray-500 dark:text-gray-400 font-medium">{label}</td>
      {values.map((v, i) => (
        <td key={i} className="px-4 py-2.5 text-right text-sm tabular-nums text-gray-900 dark:text-white">
          {v ?? "—"}
        </td>
      ))}
    </tr>
  );
}

export function FinancialsTab({ symbol }: { symbol: string }) {
  const [period, setPeriod] = useState<PeriodType>("annual");
  const { data, isLoading, error } = useFinancials(symbol, period);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-100 dark:border-gray-900 p-5 space-y-3 animate-pulse">
        {[...Array(8)].map((_, i) => <div key={i} className="h-8 skeleton rounded" />)}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 px-5 py-8 text-center text-sm text-gray-400">
        No financial data available.
      </div>
    );
  }

  const pl = data.income_statements;
  const colHeaders = pl.map(periodLabel);
  const ratios = data.key_ratios;

  // Align ratios to same years as P&L (annual only; quarterly key ratios aren't stored)
  const yearMap = Object.fromEntries(ratios.map((r) => [r.period_year, r]));
  const alignedRatios = pl.map((r) => yearMap[r.period_year] ?? null);

  return (
    <div className="space-y-6">
      {/* Period toggle */}
      <div className="flex items-center gap-1 p-1 bg-gray-100 dark:bg-gray-900 rounded-lg w-fit">
        {(["annual", "quarterly"] as PeriodType[]).map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-4 py-1.5 text-xs font-medium rounded-md transition-colors ${
              period === p
                ? "bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm"
                : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            }`}
          >
            {p === "annual" ? "Annual" : "Quarterly"}
          </button>
        ))}
      </div>

      {pl.length === 0 && (
        <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 px-5 py-8 text-center text-sm text-gray-400">
          No {period} data available. Run seed with <code>--quarterly</code> to populate quarterly data.
        </div>
      )}

      {pl.length > 0 && (
        <>
          {/* P&L */}
          <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-900 flex items-center gap-2">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Profit & Loss</h2>
              <span className="text-xs font-mono font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950 px-1.5 py-0.5 rounded">{symbol}</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 dark:border-gray-900">
                    <th className="px-4 py-3 text-left text-xs text-gray-400 font-medium w-40">₹ Cr</th>
                    {colHeaders.map((h) => (
                      <th key={h} className="px-4 py-3 text-right text-xs text-gray-400 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <Row label="Revenue" values={pl.map((r) => formatCr(r.revenue_cr))} />
                  <Row label="EBITDA" values={pl.map((r) => formatCr(r.ebitda_cr))} />
                  <Row label="PAT" values={pl.map((r) => formatCr(r.pat_cr))} />
                  <Row label="EPS (₹)" values={pl.map((r) => r.eps_basic ? `₹${parseFloat(String(r.eps_basic)).toFixed(1)}` : "—")} />
                </tbody>
              </table>
            </div>
          </div>

          {/* Key Ratios — annual only */}
          {period === "annual" && (
            <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-900 flex items-center gap-2">
                <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Key Ratios</h2>
                <span className="text-xs font-mono font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950 px-1.5 py-0.5 rounded">{symbol}</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 dark:border-gray-900">
                      <th className="px-4 py-3 text-left text-xs text-gray-400 font-medium w-40">Metric</th>
                      {colHeaders.map((h) => (
                        <th key={h} className="px-4 py-3 text-right text-xs text-gray-400 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <Row label="EBITDA Margin" values={alignedRatios.map((r) => r ? formatPercent(r.ebitda_margin_pct) : "—")} />
                    <Row label="Net Margin" values={alignedRatios.map((r) => r ? formatPercent(r.net_profit_margin_pct) : "—")} />
                    <Row label="ROE" values={alignedRatios.map((r) => r ? formatPercent(r.roe_pct) : "—")} />
                    <Row label="ROCE" values={alignedRatios.map((r) => r ? formatPercent(r.roce_pct) : "—")} />
                    <Row label="P/E" values={alignedRatios.map((r) => r ? formatNumber(r.pe_ratio) : "—")} />
                    <Row label="P/B" values={alignedRatios.map((r) => r ? formatNumber(r.pb_ratio) : "—")} />
                    <Row label="D/E" values={alignedRatios.map((r) => r ? formatNumber(r.debt_equity_ratio) : "—")} />
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
