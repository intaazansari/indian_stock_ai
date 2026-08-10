"use client";

import { AlertTriangle, ShieldAlert, RefreshCw, Sparkles } from "lucide-react";
import { useAIAnalysis, useStreamAnalysis } from "@/hooks/useAIAnalysis";
import { cn, formatUpdatedAt } from "@/lib/utils";
import type { RiskAnalysisResponse, RedFlag, RiskLevel } from "@/types/analysis";

const riskColors: Record<RiskLevel, string> = {
  low: "bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300",
  medium: "bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800 text-yellow-700 dark:text-yellow-300",
  high: "bg-orange-50 dark:bg-orange-950 border-orange-200 dark:border-orange-800 text-orange-700 dark:text-orange-300",
  critical: "bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300",
};

function RiskSection({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">{title}</p>
      <ul className="space-y-1.5">
        {items.map((r, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0 text-yellow-500" />
            {r}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function RisksTab({ symbol }: { symbol: string }) {
  const { data, isLoading } = useAIAnalysis<RiskAnalysisResponse>(symbol, "risk");
  const { isStreaming, startStream } = useStreamAnalysis(symbol, "risk");

  const header = (
    <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-900 flex items-center justify-between">
      <div className="flex items-center gap-2 flex-wrap">
        <ShieldAlert className="w-4 h-4 text-brand-500" />
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Risk Analysis</h2>
        <span className="text-xs font-mono font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950 px-1.5 py-0.5 rounded">{symbol}</span>
        {data?.generated_at && (
          <span className="text-xs text-gray-400">· Updated {formatUpdatedAt(data.generated_at)}</span>
        )}
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
        <div className="p-5 space-y-3 animate-pulse">{[...Array(5)].map((_, i) => <div key={i} className="h-8 skeleton rounded" />)}</div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
      {header}
      {!data ? (
        <div className="px-5 py-8 text-center space-y-3">
          <p className="text-sm text-gray-400">No risk analysis yet.</p>
          <button onClick={startStream} disabled={isStreaming} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors">
            <Sparkles className="w-3.5 h-3.5" />{isStreaming ? "Analysing…" : "Run Risk Analysis"}
          </button>
        </div>
      ) : (
        <div className="p-5 space-y-6">
          {/* Overall level */}
          {data.overall_risk_level && (
            <div className={cn("inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium", riskColors[data.overall_risk_level])}>
              <ShieldAlert className="w-3.5 h-3.5" />
              Overall Risk: {data.overall_risk_level.charAt(0).toUpperCase() + data.overall_risk_level.slice(1)}
            </div>
          )}

          {/* Red flags */}
          {data.red_flags?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-3">Red Flags</p>
              <div className="space-y-2">
                {data.red_flags.map((flag: RedFlag, i: number) => (
                  <div key={i} className={cn("rounded-lg border p-3", riskColors[flag.severity])}>
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-medium">{flag.title}</p>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-white/40 dark:bg-black/20 font-medium">{flag.severity}</span>
                    </div>
                    <p className="text-xs opacity-80">{flag.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <RiskSection title="Business Risks" items={data.business_risks} />
          <RiskSection title="Financial Risks" items={data.financial_risks} />
          <RiskSection title="Governance Risks" items={data.governance_risks} />
          <RiskSection title="Regulatory Risks" items={data.regulatory_risks} />
        </div>
      )}
    </div>
  );
}
