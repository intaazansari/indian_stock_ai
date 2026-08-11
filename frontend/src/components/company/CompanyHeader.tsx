"use client";

import { Brain, BookmarkPlus, BookmarkCheck, ExternalLink, Loader2, Wifi, WifiOff, ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCompany } from "@/hooks/useCompany";
import { useAuthStore } from "@/stores/useAuthStore";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { watchlistApi } from "@/lib/api/watchlist";
import { formatCr, formatPercent, cn } from "@/lib/utils";

interface CompanyHeaderProps {
  symbol: string;
}

export function CompanyHeader({ symbol }: CompanyHeaderProps) {
  const router = useRouter();
  const { data: company, isLoading, error: companyError, refetch: refetchCompany } = useCompany(symbol);

  const handleBack = () => {
    const saved = sessionStorage.getItem("company_back_url");
    if (saved) {
      sessionStorage.removeItem("company_back_url");
      router.push(saved);
    } else {
      router.back();
    }
  };
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

  if (!company) {
    const isNetwork = !(companyError as { response?: unknown } | null)?.response;
    return (
      <div className="flex flex-col gap-2">
        <button
          onClick={handleBack}
          className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white w-fit transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" />
          Back
        </button>
        <p className="text-sm text-gray-400">
          {isNetwork ? "Service is starting up — please retry in ~30 s." : "Company not found."}
        </p>
        {isNetwork && (
          <button
            onClick={() => refetchCompany()}
            className="text-xs text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-medium w-fit"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const syncLabel = getCmpSyncLabel(company.updated_at ?? null);

  return (
    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
      {/* Left: Company Identity */}
      <div>
        {/* Back button */}
        <button
          onClick={handleBack}
          className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-3 transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" />
          Back
        </button>
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
        <div className="flex flex-wrap gap-4 mt-3 items-end">
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
          {/* Market sync status badge */}
          {syncLabel && (
            <div className={cn(
              "flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border self-end mb-0.5",
              syncLabel.isLive
                ? "bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800"
                : "bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 border-gray-200 dark:border-gray-700"
            )}>
              {syncLabel.isLive
                ? <Wifi className="w-3 h-3" />
                : <WifiOff className="w-3 h-3" />
              }
              {syncLabel.label}
            </div>
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

/**
 * Returns a formatted price-sync label based on when CMP was last updated.
 * Shows "Live" during NSE trading hours (Mon–Fri 9:15–15:30 IST),
 * otherwise "Closed · Last HH:MM IST" or "Closed · DD MMM HH:MM IST".
 */
function getCmpSyncLabel(updatedAt: string | null): { label: string; isLive: boolean } | null {
  if (!updatedAt) return null;

  const now = new Date();
  const updated = new Date(updatedAt);

  // Convert to IST (UTC+5:30)
  const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000;
  const nowIST = new Date(now.getTime() + IST_OFFSET_MS);
  const updatedIST = new Date(updated.getTime() + IST_OFFSET_MS);

  const dayOfWeek = nowIST.getUTCDay(); // 0=Sun … 6=Sat
  const totalMinutes = nowIST.getUTCHours() * 60 + nowIST.getUTCMinutes();
  const isWeekday = dayOfWeek >= 1 && dayOfWeek <= 5;
  const isMarketOpen =
    isWeekday && totalMinutes >= 9 * 60 + 15 && totalMinutes <= 15 * 60 + 30;

  const hh = String(updatedIST.getUTCHours()).padStart(2, "0");
  const mm = String(updatedIST.getUTCMinutes()).padStart(2, "0");
  const timeStr = `${hh}:${mm} IST`;

  const todayIST = nowIST;
  const isSameDay =
    updatedIST.getUTCFullYear() === todayIST.getUTCFullYear() &&
    updatedIST.getUTCMonth()    === todayIST.getUTCMonth() &&
    updatedIST.getUTCDate()     === todayIST.getUTCDate();

  const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const datePrefix = isSameDay
    ? ""
    : `${updatedIST.getUTCDate()} ${MONTHS[updatedIST.getUTCMonth()]} `;

  if (isMarketOpen) {
    return { label: `Live · ${timeStr}`, isLive: true };
  }
  return { label: `Closed · Last ${datePrefix}${timeStr}`, isLive: false };
}
