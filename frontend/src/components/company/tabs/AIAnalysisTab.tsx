"use client";

import { Sparkles, RefreshCw } from "lucide-react";
import { useAIAnalysis, useStreamAnalysis } from "@/hooks/useAIAnalysis";
import { cn } from "@/lib/utils";

interface Props {
  symbol: string;
  agentType: "valuation" | "quality" | "risk" | "research" | "financial";
  title: string;
}

export function AIAnalysisTab({ symbol, agentType, title }: Props) {
  const { data, isLoading } = useAIAnalysis(symbol, agentType);
  const { streamContent, isStreaming, startStream } = useStreamAnalysis(symbol, agentType);

  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-900 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-brand-500" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h2>
        </div>
        <button
          onClick={startStream}
          disabled={isStreaming || isLoading}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={cn("w-3 h-3", isStreaming && "animate-spin")} />
          {isStreaming ? "Analysing…" : data ? "Refresh" : "Analyse"}
        </button>
      </div>

      {isLoading && (
        <div className="p-5 space-y-3 animate-pulse">
          <div className="h-4 w-full skeleton rounded" />
          <div className="h-4 w-3/4 skeleton rounded" />
          <div className="h-20 skeleton rounded-lg" />
        </div>
      )}

      {isStreaming && (
        <div className="px-5 py-4 text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
          <p className="whitespace-pre-wrap">{streamContent || "Analysing…"}</p>
          <div className="mt-1 inline-block w-2 h-4 bg-brand-500 animate-pulse" />
        </div>
      )}

      {!isLoading && !isStreaming && !!data && (
        <div className="px-5 py-4 space-y-4">
          <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed font-sans">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}

      {!isLoading && !isStreaming && !data && (
        <div className="px-5 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
          No analysis yet. Click <strong>Analyse</strong> to generate.
        </div>
      )}
    </div>
  );
}
