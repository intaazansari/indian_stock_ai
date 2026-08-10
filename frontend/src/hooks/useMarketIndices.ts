"use client";

import { useQuery } from "@tanstack/react-query";
import { marketApi } from "@/lib/api/market";
import { getNseMarketStatus } from "@/lib/utils";

export function useMarketIndices() {
  return useQuery({
    queryKey: ["market", "indices"],
    queryFn: marketApi.getIndices,
    // Only poll during NSE trading hours; stop when market is closed
    refetchInterval: () => getNseMarketStatus().isOpen ? 60_000 : false,
    staleTime: 30_000,
  });
}
