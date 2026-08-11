"use client";

import { usePeers } from "@/hooks/useCompany";
import { formatCr, formatPercent, cn } from "@/lib/utils";
import Link from "next/link";

interface Props { symbol: string }

function Num({ value, suffix = "", good = "high" }: {
  value: number | string | null | undefined;
  suffix?: string;
  good?: "high" | "low" | "none";
}) {
  if (value === null || value === undefined) return <span className="text-gray-300 dark:text-gray-600">—</span>;
  const n = Number(value);
  if (isNaN(n)) return <span className="text-gray-300 dark:text-gray-600">—</span>;

  let color = "";
  if (good === "high") color = n >= 15 ? "text-green-600 dark:text-green-400" : n >= 10 ? "" : "text-red-500 dark:text-red-400";
  if (good === "low")  color = n <= 1  ? "text-green-600 dark:text-green-400" : n <= 2  ? "" : "text-red-500 dark:text-red-400";

  return (
    <span className={cn("tabular-nums", color)}>
      {n.toFixed(1)}{suffix}
    </span>
  );
}

export function PeersTab({ symbol }: Props) {
  const { data: peers, isLoading, error, refetch, isFetching } = usePeers(symbol);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-100 dark:border-gray-900 p-5 space-y-3 animate-pulse">
        {[...Array(5)].map((_, i) => <div key={i} className="h-12 bg-gray-100 dark:bg-gray-900 rounded" />)}
      </div>
    );
  }

  if (error || !peers?.length) {
    const isNetwork = error && !(error as { response?: unknown })?.response;
    return (
      <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 px-5 py-8 text-center space-y-3">
        <p className="text-sm text-gray-400">
          {isNetwork ? "Service is starting up — this may take ~30 s on first load." : "No peer data available."}
        </p>
        {isNetwork && (
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 transition-colors disabled:opacity-50"
          >
            <svg className={`w-3 h-3 ${isFetching ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            {isFetching ? "Loading…" : "Retry"}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-900 flex items-center gap-2">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Peer Comparison</h2>
        <span className="text-xs font-mono font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950 px-1.5 py-0.5 rounded">{symbol}</span>
        <span className="text-xs text-gray-400">· {peers.length} companies</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 dark:border-gray-900 text-xs text-gray-400 dark:text-gray-500">
              <th className="px-5 py-3 text-left font-medium sticky left-0 bg-white dark:bg-gray-950">Company</th>
              <th className="px-4 py-3 text-right font-medium">Mkt Cap</th>
              <th className="px-4 py-3 text-right font-medium">CMP</th>
              <th className="px-4 py-3 text-right font-medium">PE</th>
              <th className="px-4 py-3 text-right font-medium">PB</th>
              <th className="px-4 py-3 text-right font-medium">ROE %</th>
              <th className="px-4 py-3 text-right font-medium">ROCE %</th>
              <th className="px-4 py-3 text-right font-medium">NPM %</th>
              <th className="px-4 py-3 text-right font-medium">D/E</th>
              <th className="px-4 py-3 text-right font-medium">Rev Gr %</th>
              <th className="px-4 py-3 text-right font-medium">Promoter</th>
            </tr>
          </thead>
          <tbody>
            {peers.map((peer) => (
              <tr
                key={peer.id}
                className={cn(
                  "border-b border-gray-50 dark:border-gray-900/50 hover:bg-gray-50 dark:hover:bg-gray-900/30 transition-colors",
                  peer.nse_symbol === symbol && "bg-brand-50 dark:bg-brand-950/20"
                )}
              >
                <td className="px-5 py-3 sticky left-0 bg-inherit">
                  <Link
                    href={`/company/${peer.nse_symbol}`}
                    className="font-medium text-gray-900 dark:text-white hover:text-brand-600 dark:hover:text-brand-400"
                  >
                    {peer.nse_symbol}
                    {peer.nse_symbol === symbol && (
                      <span className="ml-1.5 text-xs text-brand-500 font-normal">(you)</span>
                    )}
                  </Link>
                  <p className="text-xs text-gray-400 dark:text-gray-500 truncate max-w-[160px]">{peer.name}</p>
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-gray-700 dark:text-gray-300">
                  {formatCr(peer.market_cap_cr)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-gray-700 dark:text-gray-300">
                  {peer.cmp ? `₹${parseFloat(String(peer.cmp)).toFixed(0)}` : "—"}
                </td>
                <td className="px-4 py-3 text-right"><Num value={peer.pe_ratio} good="none" /></td>
                <td className="px-4 py-3 text-right"><Num value={peer.pb_ratio} good="none" /></td>
                <td className="px-4 py-3 text-right"><Num value={peer.roe_pct} suffix="%" good="high" /></td>
                <td className="px-4 py-3 text-right"><Num value={peer.roce_pct} suffix="%" good="high" /></td>
                <td className="px-4 py-3 text-right"><Num value={peer.net_profit_margin_pct} suffix="%" good="high" /></td>
                <td className="px-4 py-3 text-right"><Num value={peer.debt_equity_ratio} good="low" /></td>
                <td className="px-4 py-3 text-right"><Num value={peer.revenue_growth_pct} suffix="%" good="high" /></td>
                <td className="px-4 py-3 text-right tabular-nums text-gray-700 dark:text-gray-300">
                  {formatPercent(peer.promoter_holding_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="px-5 py-2 text-xs text-gray-400 dark:text-gray-600 border-t border-gray-50 dark:border-gray-900/50">
        Green = strong (&gt;15% ROE/ROCE, D/E &lt;1) · Red = weak · Latest annual data
      </p>
    </div>
  );
}

