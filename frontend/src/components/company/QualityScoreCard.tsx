"use client";

import { useQualityScore } from "@/hooks/useAIAnalysis";
import { cn, getScoreColor, getScoreBg } from "@/lib/utils";
import type { ScoreItem } from "@/types/analysis";

interface QualityScoreCardProps {
  symbol: string;
}

export function QualityScoreCard({ symbol }: QualityScoreCardProps) {
  const { data, isLoading } = useQualityScore(symbol);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-100 dark:border-gray-900 p-5 space-y-4">
        <div className="h-5 w-32 skeleton" />
        <div className="h-16 skeleton rounded-lg" />
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-10 skeleton rounded" />
        ))}
      </div>
    );
  }

  if (!data) return null;

  const dimensions: ScoreItem[] = [
    data.business_quality,
    data.financial_health,
    data.management_quality,
    data.growth_quality,
    data.valuation,
  ];

  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-900 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Quality Score</h2>
        <span className="text-xs text-gray-400 dark:text-gray-500">AI-generated</span>
      </div>

      {/* Overall Score */}
      <div className={cn("mx-4 mt-4 mb-1 rounded-lg border p-4 text-center", getScoreBg(data.overall_score))}>
        <div className={cn("text-4xl font-bold tabular-nums", getScoreColor(data.overall_score))}>
          {data.overall_score}
          <span className="text-lg font-normal text-gray-400 dark:text-gray-500">/10</span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-relaxed line-clamp-2">
          {data.summary}
        </p>
      </div>

      {/* Dimension Scores */}
      <div className="px-4 pb-4 mt-3 space-y-2">
        {dimensions.map((dim) => (
          <ScoreDimension key={dim.label} item={dim} />
        ))}
      </div>

      {/* Strengths & Weaknesses */}
      {(data.strengths.length > 0 || data.weaknesses.length > 0) && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-50 dark:border-gray-900 pt-3">
          {data.strengths.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-green-700 dark:text-green-400 mb-1.5">
                Strengths
              </p>
              <ul className="space-y-1">
                {data.strengths.map((s, i) => (
                  <li key={i} className="text-xs text-gray-600 dark:text-gray-400 flex gap-1.5">
                    <span className="text-green-500 mt-0.5">+</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {data.weaknesses.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-red-700 dark:text-red-400 mb-1.5">
                Weaknesses
              </p>
              <ul className="space-y-1">
                {data.weaknesses.map((w, i) => (
                  <li key={i} className="text-xs text-gray-600 dark:text-gray-400 flex gap-1.5">
                    <span className="text-red-500 mt-0.5">−</span>
                    {w}
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

function ScoreDimension({ item }: { item: ScoreItem }) {
  const pct = (item.score / 10) * 100;

  return (
    <div className="group cursor-default">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-600 dark:text-gray-400">{item.label}</span>
        <span className={cn("text-xs font-bold tabular-nums", getScoreColor(item.score))}>
          {item.score}/10
        </span>
      </div>
      {/* Progress bar */}
      <div className="h-1.5 bg-gray-100 dark:bg-gray-900 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            item.score >= 8
              ? "bg-green-500"
              : item.score >= 6
              ? "bg-brand-500"
              : item.score >= 4
              ? "bg-yellow-500"
              : "bg-red-500"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      {/* Explanation on hover — shown as tooltip via title, full text on mobile */}
      <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 leading-relaxed line-clamp-2 hidden group-hover:block">
        {item.explanation}
      </p>
    </div>
  );
}
