"use client";

import { useQuery } from "@tanstack/react-query";
import { marketApi } from "@/lib/api/market";

export function useMarketIndices() {
  return useQuery({
    queryKey: ["market", "indices"],
    queryFn: marketApi.getIndices,
    refetchInterval: 60_000, // refresh every 60s
    staleTime: 30_000,
  });
}
