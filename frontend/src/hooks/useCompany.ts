import { useQuery } from "@tanstack/react-query";
import { companiesApi } from "@/lib/api/companies";
import type { Company } from "@/types/company";

export function useCompany(symbol: string) {
  return useQuery<Company>({
    queryKey: ["company", symbol],
    queryFn: () => companiesApi.getBySymbol(symbol),
    staleTime: 5 * 60 * 1000,    // 5 minutes — company data changes rarely
    enabled: Boolean(symbol),
  });
}

export function usePeers(symbol: string) {
  return useQuery({
    queryKey: ["company", symbol, "peers"],
    queryFn: () => companiesApi.getPeers(symbol),
    staleTime: 30 * 60 * 1000,   // 30 minutes
    enabled: Boolean(symbol),
  });
}
