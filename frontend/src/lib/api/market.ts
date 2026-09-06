import { apiClient } from "./client";

export interface MarketIndex {
  symbol: string;
  name: string;
  short: string;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  as_of?: string;
}

export interface MarketMover {
  symbol: string;
  company: string;
  close: string;
  previous_close: string;
  change_pct: string;
  rank: number;
}

export interface MarketMoversResponse {
  date: string | null;
  gainers: MarketMover[];
  losers: MarketMover[];
}

export const marketApi = {
  getIndices: async (): Promise<MarketIndex[]> => {
    const { data } = await apiClient.get<MarketIndex[]>("/market/indices");
    return data;
  },

  getMovers: async (limit = 10): Promise<MarketMoversResponse> => {
    const { data } = await apiClient.get<MarketMoversResponse>("/market/movers", {
      params: { limit },
    });
    return data;
  },
};
