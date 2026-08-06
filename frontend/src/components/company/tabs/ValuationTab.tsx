"use client";

import { TrendingDown, TrendingUp, RefreshCw, Sparkles } from "lucide-react";
import { useAIAnalysis, useStreamAnalysis } from "@/hooks/useAIAnalysis";
import { cn, formatNumber } from "@/lib/utils";
import type { ValuationAnalysisResponse } from "@/types/analysis";

function AnalysePrompt({ onAnalyse, isStreaming }: { onAnalyse: () => void; isStreaming: boolean }) {
  return (
    <div className="px-5 py-8 text-center space-y-3">
      <p className="text-sm text-gray-400">No valuation analysis yet.</p>
      <button
        onClick={onAnalyse}
        disabled={isStreaming}
        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors"
      >
        <Sparkles className="w-3.5 h-3.5" />
        {isStreaming ? "Analysing…" : "Run Valuation Analysis"}
      </button>
    </div>
  );
}

export function ValuationTab({ symbol }: { symbol: string }) {
  const { data, isLoading } = useAIAnalysis<ValuationAnalysisResponse>(symbol, "valuation");
  const { isStreaming, startStream } = useStreamAnalysis(symbol, "valuation");

  const header = (
    <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-900 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-brand-500" />
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Valuation Analysis</h2>
      </div>
      {data && (
        <button onClick={startStream} disabled={isStreaming} className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50">
          <RefreshCw className={cn("w-3 h-3", isStreaming && "animate-spin")} />
          {isStreaming ? "Analysing…" : "Refresh"}
        </button>
      )}
    </div>
  );

  if (isLoading || isStreaming) {
    return (
      <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
        {header}
        <div className="p-5 space-y-3 animate-pulse">
          {[...Array(4)].map((_, i) => <div key={i} className="h-10 skeleton rounded" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
      {header}
      {!data
        ? <AnalysePrompt onAnalyse={startStream} isStreaming={isStreaming} />
        : (
          <div className="p-5 space-y-6">
            {/* PE Comparison */}
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Current P/E", value: data.current_pe, highlight: true },
                { label: "Sector Median P/E", value: data.sector_median_pe },
                { label: "Historical Median P/E", value: data.historical_pe_median },
              ].map(({ label, value, highlight }) => (
                <div key={label} className={cn("rounded-lg border p-4 text-center", highlight ? "border-brand-200 dark:border-brand-800 bg-brand-50 dark:bg-brand-950" : "border-gray-100 dark:border-gray-900")}>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mb-1">{label}</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums">{value ?? "—"}x</p>
                </div>
              ))}
            </div>

            {/* Verdict banner */}
            <div className={cn("flex items-center gap-3 rounded-lg p-4 border", data.is_overvalued ? "bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800" : "bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800")}>
              {data.is_overvalued ? <TrendingDown className="w-5 h-5 text-red-500 shrink-0" /> : <TrendingUp className="w-5 h-5 text-green-500 shrink-0" />}
              <div>
                <p className={cn("text-sm font-semibold", data.is_overvalued ? "text-red-700 dark:text-red-300" : "text-green-700 dark:text-green-300")}>
                  {data.is_overvalued ? "Appears Overvalued" : "Appears Fairly Valued / Undervalued"}
                </p>
                {data.upside_downside_pct != null && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {data.upside_downside_pct > 0 ? "+" : ""}{formatNumber(data.upside_downside_pct)}% upside to fair value
                  </p>
                )}
              </div>
            </div>

            {/* Commentary */}
            <div>
              <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">Valuation Commentary</p>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{data.valuation_commentary}</p>
            </div>

            {/* Methodology + Assumptions */}
            {data.valuation_methodology && (
              <div>
                <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-1">Methodology</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">{data.valuation_methodology}</p>
              </div>
            )}
            {data.key_assumptions?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">Key Assumptions</p>
                <ul className="space-y-1">
                  {data.key_assumptions.map((a, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <span className="mt-1.5 w-1 h-1 rounded-full bg-gray-400 shrink-0" />
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
    </div>
  );
}
