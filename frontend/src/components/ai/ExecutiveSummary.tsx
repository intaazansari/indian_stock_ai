"use client";

import { Sparkles, RefreshCw, AlertCircle, TrendingUp } from "lucide-react";
import { useExecutiveSummary, useStreamAnalysis } from "@/hooks/useAIAnalysis";
import { getScoreColor, cn, formatUpdatedAt } from "@/lib/utils";

interface ExecutiveSummaryProps {
  symbol: string;
}

export function ExecutiveSummaryCard({ symbol }: ExecutiveSummaryProps) {
  const { data, isLoading, error } = useExecutiveSummary(symbol);
  const { streamContent, isStreaming, startStream } = useStreamAnalysis(symbol, "summary");

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-100 dark:border-gray-900 p-5 space-y-4">
        <div className="h-5 w-40 skeleton" />
        <div className="h-4 w-full skeleton" />
        <div className="h-4 w-3/4 skeleton" />
        <div className="h-20 skeleton rounded-lg" />
      </div>
    );
  }

  if (error && !data) {
    const is404 = (error as { status?: number })?.status === 404 ||
      (error as { response?: { status?: number } })?.response?.status === 404;
    return (
      <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
            <Sparkles className="w-4 h-4 shrink-0 text-brand-400" />
            <p className="text-sm">
              {is404 ? "No AI analysis yet." : "Failed to load analysis."}
            </p>
          </div>
          <button
            onClick={startStream}
            disabled={isStreaming}
            className="flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3 h-3", isStreaming && "animate-spin")} />
            {isStreaming ? "Analysing…" : "Analyse"}
          </button>
        </div>
        {isStreaming && (
          <div className="mt-4 text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            <p className="whitespace-pre-wrap">{streamContent || "Analysing…"}</p>
            <div className="mt-1 inline-block w-2 h-4 bg-brand-500 animate-pulse" />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-900 flex items-center justify-between">
        <div className="flex items-center gap-2 flex-wrap">
          <Sparkles className="w-4 h-4 text-brand-500" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">AI Summary</h2>
          <span className="text-xs font-mono font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950 px-1.5 py-0.5 rounded">{symbol}</span>
          {data?.generated_at && (
            <span className="text-xs text-gray-400">· Updated {formatUpdatedAt(data.generated_at)}</span>
          )}
        </div>
        <button
          onClick={startStream}
          disabled={isStreaming}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={cn("w-3 h-3", isStreaming && "animate-spin")} />
          {isStreaming ? "Analysing…" : "Refresh"}
        </button>
      </div>

      {/* Streaming content */}
      {isStreaming && (
        <div className="px-5 py-4 text-sm text-gray-700 dark:text-gray-300 leading-relaxed border-b border-gray-100 dark:border-gray-900">
          <p className="whitespace-pre-wrap">{streamContent || "Analysing…"}</p>
          <div className="mt-1 inline-block w-2 h-4 bg-brand-500 animate-pulse" />
        </div>
      )}

      {data && !isStreaming && (
        <div className="px-5 py-4 space-y-4">
          {/* One-liner */}
          <p className="text-base font-medium text-gray-800 dark:text-gray-200 leading-relaxed">
            {data.one_liner}
          </p>

          {/* Business story */}
          <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
            {data.business_story}
          </p>

          {/* Investment case */}
          <div className="rounded-lg bg-brand-50 dark:bg-brand-950 border border-brand-100 dark:border-brand-900 p-4">
            <p className="text-xs font-semibold text-brand-700 dark:text-brand-300 mb-1.5">
              Investment Case
            </p>
            <p className="text-sm text-brand-800 dark:text-brand-200 leading-relaxed">
              {data.investment_case}
            </p>
          </div>

          {/* 3-Score Row */}
          <div className="grid grid-cols-3 gap-3">
            <ScoreBadge label="Quality" score={data.quality_score} />
            <ScoreBadge label="Valuation" score={data.valuation_score} />
            <ScoreBadge label="Risk" score={data.risk_score} inverted />
          </div>

          {/* Key monitorables */}
          <div>
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
              Key Monitorables
            </p>
            <ul className="space-y-1.5">
              {data.key_monitorables.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <TrendingUp className="w-3.5 h-3.5 text-brand-500 shrink-0 mt-0.5" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Overall verdict */}
          <div className="rounded-lg bg-gray-50 dark:bg-gray-900 p-4">
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5">
              Overall Verdict
            </p>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed italic">
              &ldquo;{data.overall_verdict}&rdquo;
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function ScoreBadge({
  label,
  score,
  inverted = false,
}: {
  label: string;
  score: number;
  inverted?: boolean;
}) {
  const displayScore = inverted ? 10 - score + score : score; // for risk, higher = lower risk
  return (
    <div className="text-center rounded-lg border border-gray-100 dark:border-gray-900 py-3">
      <div className={cn("text-xl font-bold tabular-nums", getScoreColor(score))}>
        {score}
        <span className="text-xs font-normal text-gray-400">/10</span>
      </div>
      <div className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}
