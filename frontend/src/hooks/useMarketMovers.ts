"use client";

import { useQuery } from "@tanstack/react-query";
import { marketApi } from "@/lib/api/market";
import { getNseMarketStatus } from "@/lib/utils";

/**
 * Top Gainers/Losers for the latest trading day (populated once per day by
 * the backend's daily price-refresh job — Mon-Fri after NSE close).
 * No need to poll while the market is open; the data only changes once a day.
 */
export function useMarketMovers(limit = 10) {
  return useQuery({
    queryKey: ["market", "movers", limit],
    queryFn: () => marketApi.getMovers(limit),
    // Refresh occasionally in case today's job just landed; no need for
    // fast polling since this data updates at most once per trading day.
    refetchInterval: () => getNseMarketStatus().isOpen ? false : 5 * 60_000,
    staleTime: 5 * 60_000,
  });
}
