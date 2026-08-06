import { apiClient } from "./client";
import type { PaginatedResponse } from "./types";

export interface ScreenerResult {
  id: string;
  name: string;
  nse_symbol: string | null;
  sector: string | null;
  industry: string | null;
  market_cap_cr: number | null;
  cmp: number | null;
  promoter_holding_pct: number | null;
  pe_ratio: number | null;
  pb_ratio: number | null;
  roe_pct: number | null;
  roce_pct: number | null;
  net_profit_margin_pct: number | null;
  ebitda_margin_pct: number | null;
  debt_equity_ratio: number | null;
  interest_coverage: number | null;
  current_ratio: number | null;
  revenue_growth_pct: number | null;
  pat_growth_pct: number | null;
  dividend_yield_pct: number | null;
}

export type SortField =
  | "market_cap"
  | "pe_ratio"
  | "pb_ratio"
  | "roe_pct"
  | "roce_pct"
  | "revenue_growth_pct"
  | "pat_growth_pct"
  | "debt_equity_ratio"
  | "net_profit_margin_pct"
  | "dividend_yield_pct";

export interface ScreenerFilter {
  sector?: string | null;
  industry?: string | null;
  market_cap_min?: number | null;
  market_cap_max?: number | null;
  pe_min?: number | null;
  pe_max?: number | null;
  pb_min?: number | null;
  pb_max?: number | null;
  roe_min?: number | null;
  roce_min?: number | null;
  net_profit_margin_min?: number | null;
  debt_equity_max?: number | null;
  current_ratio_min?: number | null;
  revenue_growth_min?: number | null;
  pat_growth_min?: number | null;
  promoter_holding_min?: number | null;
  sort_by?: SortField;
  sort_order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export const screenerApi = {
  getSectors: async (): Promise<string[]> => {
    const { data } = await apiClient.get<string[]>("/screener/sectors");
    return data;
  },

  filter: async (
    filters: ScreenerFilter
  ): Promise<PaginatedResponse<ScreenerResult>> => {
    const { data } = await apiClient.post<PaginatedResponse<ScreenerResult>>(
      "/screener/filter",
      filters
    );
    return data;
  },
};
