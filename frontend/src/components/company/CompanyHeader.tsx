"use client";

import { Brain, BookmarkPlus, BookmarkCheck, ExternalLink, Loader2 } from "lucide-react";
import { useCompany } from "@/hooks/useCompany";
import { useAuthStore } from "@/stores/useAuthStore";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { watchlistApi } from "@/lib/api/watchlist";
import { formatCr, formatPercent, cn } from "@/lib/utils";

interface CompanyHeaderProps {
  symbol: string;
}

export function CompanyHeader({ symbol }: CompanyHeaderProps) {
  const { data: company, isLoading } = useCompany(symbol);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const queryClient = useQueryClient();

  // Fetch server-side watchlist to derive current watch state
  const { data: watchlistItems = [] } = useQuery({
    queryKey: ["watchlist"],
    queryFn: watchlistApi.list,
    enabled: isAuthenticated,
    staleTime: 5 * 60_000,
  });
  const watchlistEntry = company
    ? watchlistItems.find((w) => w.nse_symbol === symbol)
    : undefined;
  const inWatchlist = Boolean(watchlistEntry);

  const addMutation = useMutation({
    mutationFn: () => watchlistApi.add(company!.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
  });
  const removeMutation = useMutation({
    mutationFn: () => watchlistApi.remove(company!.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
  });
  const isMutating = addMutation.isPending || removeMutation.isPending;

  const handleWatchlistToggle = () => {
    if (!isAuthenticated) {
      window.location.href = "/login";
      return;
    }
    if (inWatchlist) {
      removeMutation.mutate();
    } else {
      addMutation.mutate();
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        <div className="h-8 w-64 skeleton" />
        <div className="h-4 w-40 skeleton" />
      </div>
    );
  }

  if (!company) return null;

  return (
    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
      {/* Left: Company Identity */}
      <div>
        <div className="flex items-center gap-3 mb-1">
          {/* Company name */}
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {company.name}
          </h1>
          {/* NSE Symbol badge */}
          {company.nse_symbol && (
            <span className="px-2 py-0.5 rounded text-xs font-bold font-mono bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-300 border border-brand-100 dark:border-brand-900">
              NSE: {company.nse_symbol}
            </span>
          )}
        </div>

        {/* Sector / Industry breadcrumb */}
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {[company.sector, company.industry].filter(Boolean).join(" · ")}
        </p>

        {/* Key metrics row */}
        <div className="flex flex-wrap gap-4 mt-3">
          <MetricPill label="Market Cap" value={formatCr(company.market_cap_cr)} />
          <MetricPill label="CMP" value={company.cmp ? `₹${parseFloat(String(company.cmp)).toFixed(0)}` : "—"} />
          <MetricPill label="Promoter" value={formatPercent(company.promoter_holding_pct)} />
          {company.face_value && (
            <MetricPill label="Face Value" value={`₹${company.face_value}`} />
          )}
          {company.week52_high && (
            <MetricPill label="52W High" value={`₹${parseFloat(String(company.week52_high)).toFixed(0)}`} />
          )}
          {company.week52_low && (
            <MetricPill label="52W Low" value={`₹${parseFloat(String(company.week52_low)).toFixed(0)}`} />
          )}
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Watchlist toggle */}
        <button
          onClick={handleWatchlistToggle}
          disabled={isMutating}
          className={cn(
            "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors border",
            inWatchlist
              ? "bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-300 border-brand-200 dark:border-brand-800"
              : "bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700"
          )}
        >
          {isMutating ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : inWatchlist ? (
            <BookmarkCheck className="w-4 h-4" />
          ) : (
            <BookmarkPlus className="w-4 h-4" />
          )}
          {inWatchlist ? "Watching" : isAuthenticated ? "Watch" : "Watch"}
        </button>

        {/* BSE link */}
        {company.bse_code && (
          <a
            href={`https://www.bseindia.com/stock-share-price/${company.bse_code}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            BSE
          </a>
        )}
      </div>
    </div>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-gray-400 dark:text-gray-500">{label}</span>
      <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">{value}</span>
    </div>
  );
}
