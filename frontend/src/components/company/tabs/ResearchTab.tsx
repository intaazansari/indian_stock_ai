"use client";

import { Sparkles, RefreshCw, TrendingUp, Shield, Users, Zap, Globe } from "lucide-react";
import { useAIAnalysis, useStreamAnalysis } from "@/hooks/useAIAnalysis";
import { cn } from "@/lib/utils";

interface ResearchData {
  one_liner?: string;
  business_model?: string;
  competitive_moat?: string;
  key_customers?: string;
  key_risks?: string[];
  growth_drivers?: string[];
  sector_tailwinds?: string;
  raw_response?: string;
}

interface Props {
  symbol: string;
}

function Section({
  icon: Icon,
  label,
  children,
}: {
  icon: React.ElementType;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5">
        <Icon className="w-3.5 h-3.5 text-brand-500" />
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {label}
        </span>
      </div>
      <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{children}</div>
    </div>
  );
}

function TagList({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-wrap gap-2 mt-1">
      {items.map((item, i) => (
        <li
          key={i}
          className="text-xs px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
        >
          {item}
        </li>
      ))}
    </ul>
  );
}

export function ResearchTab({ symbol }: Props) {
  const { data, isLoading } = useAIAnalysis<ResearchData>(symbol, "research");
  const { streamContent, isStreaming, startStream } = useStreamAnalysis(symbol, "research");

  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-900 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-brand-500" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Business Research</h2>
        </div>
        <button
          onClick={startStream}
          disabled={isStreaming || isLoading}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={cn("w-3 h-3", isStreaming && "animate-spin")} />
          {isStreaming ? "Analysing…" : data ? "Refresh" : "Generate Report"}
        </button>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="p-5 space-y-4 animate-pulse">
          <div className="h-4 w-3/4 skeleton rounded" />
          <div className="h-16 skeleton rounded-lg" />
          <div className="h-16 skeleton rounded-lg" />
        </div>
      )}

      {/* Streaming */}
      {isStreaming && (
        <div className="px-5 py-4 text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
          <p className="whitespace-pre-wrap">{streamContent || "Generating research report…"}</p>
          <span className="inline-block w-2 h-4 bg-brand-500 animate-pulse ml-1" />
        </div>
      )}

      {/* Structured result */}
      {!isLoading && !isStreaming && data && !data.raw_response && (
        <div className="px-5 py-5 space-y-5 divide-y divide-gray-100 dark:divide-gray-900">
          {data.one_liner && (
            <div className="pb-4">
              <p className="text-base font-medium text-gray-900 dark:text-white leading-snug">
                {data.one_liner}
              </p>
            </div>
          )}

          <div className="pt-4 space-y-5">
            {data.business_model && (
              <Section icon={Zap} label="Business Model">
                {data.business_model}
              </Section>
            )}

            {data.competitive_moat && (
              <Section icon={Shield} label="Competitive Moat">
                {data.competitive_moat}
              </Section>
            )}

            {data.key_customers && (
              <Section icon={Users} label="Key Customers">
                {data.key_customers}
              </Section>
            )}

            {data.sector_tailwinds && (
              <Section icon={Globe} label="Sector Tailwinds">
                {data.sector_tailwinds}
              </Section>
            )}

            {data.growth_drivers && data.growth_drivers.length > 0 && (
              <Section icon={TrendingUp} label="Growth Drivers">
                <TagList items={data.growth_drivers} />
              </Section>
            )}

            {data.key_risks && data.key_risks.length > 0 && (
              <Section icon={Shield} label="Key Risks">
                <ul className="space-y-1 mt-1">
                  {data.key_risks.map((risk, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
                      {risk}
                    </li>
                  ))}
                </ul>
              </Section>
            )}
          </div>
        </div>
      )}

      {/* Raw text fallback (if JSON parse fails but content exists) */}
      {!isLoading && !isStreaming && data?.raw_response && (
        <div className="px-5 py-5 space-y-2">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Research Notes</p>
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
            {data.raw_response}
          </p>
          <button
            onClick={startStream}
            className="mt-3 text-xs text-brand-500 hover:underline"
          >
            Regenerate with fresh data →
          </button>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isStreaming && !data && (
        <div className="px-5 py-12 text-center">
          <Sparkles className="w-8 h-8 text-gray-200 dark:text-gray-800 mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            No research report yet. Generate one with AI analysis.
          </p>
          <button
            onClick={startStream}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-brand-500 text-white hover:bg-brand-600 transition-colors"
          >
            Generate Research Report
          </button>
        </div>
      )}
    </div>
  );
}
