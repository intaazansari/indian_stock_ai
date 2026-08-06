"use client";

import { RefreshCw, Sparkles } from "lucide-react";
import { useAIAnalysis, useStreamAnalysis } from "@/hooks/useAIAnalysis";
import { cn, getScoreColor, getScoreBg } from "@/lib/utils";
import type { QualityScoreResponse, ScoreItem } from "@/types/analysis";

function ScoreBar({ item }: { item: ScoreItem }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{item.label}</span>
        <span className={cn("text-sm font-bold tabular-nums", getScoreColor(item.score))}>
          {item.score}<span className="text-xs font-normal text-gray-400">/10</span>
        </span>
      </div>
      <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-1.5">
        <div
          className={cn("h-1.5 rounded-full transition-all", getScoreBg(item.score))}
          style={{ width: `${item.score * 10}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{item.explanation}</p>
    </div>
  );
}

export function QualityTab({ symbol }: { symbol: string }) {
  const { data, isLoading } = useAIAnalysis<QualityScoreResponse>(symbol, "quality");
  const { isStreaming, startStream } = useStreamAnalysis(symbol, "quality");

  const header = (
    <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-900 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-brand-500" />
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Business Quality</h2>
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
        <div className="p-5 space-y-4 animate-pulse">{[...Array(5)].map((_, i) => <div key={i} className="h-12 skeleton rounded" />)}</div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
      {header}
      {!data ? (
        <div className="px-5 py-8 text-center space-y-3">
          <p className="text-sm text-gray-400">No quality analysis yet.</p>
          <button onClick={startStream} disabled={isStreaming} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors">
            <Sparkles className="w-3.5 h-3.5" />{isStreaming ? "Analysing…" : "Run Quality Analysis"}
          </button>
        </div>
      ) : (
        <div className="p-5 space-y-6">
          {/* Overall score */}
          <div className="flex items-center gap-4 p-4 rounded-xl bg-gray-50 dark:bg-gray-900">
            <div className={cn("text-4xl font-bold tabular-nums", getScoreColor(data.overall_score))}>
              {data.overall_score}
            </div>
            <div>
              <p className="text-xs text-gray-400 dark:text-gray-500 mb-1">Overall Quality Score</p>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{data.summary}</p>
            </div>
          </div>

          {/* 5 dimensions */}
          <div className="space-y-5">
            {[data.business_quality, data.financial_health, data.management_quality, data.growth_quality, data.valuation]
              .filter(Boolean)
              .map((item) => <ScoreBar key={item.label} item={item} />)}
          </div>

          {/* Strengths / Weaknesses */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.strengths?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-green-600 dark:text-green-400 uppercase tracking-wide mb-2">Strengths</p>
                <ul className="space-y-1">
                  {data.strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <span className="mt-2 w-1 h-1 rounded-full bg-green-500 shrink-0" />{s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {data.weaknesses?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-red-600 dark:text-red-400 uppercase tracking-wide mb-2">Weaknesses</p>
                <ul className="space-y-1">
                  {data.weaknesses.map((w, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <span className="mt-2 w-1 h-1 rounded-full bg-red-500 shrink-0" />{w}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
