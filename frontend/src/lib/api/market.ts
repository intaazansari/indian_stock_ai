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

export const marketApi = {
  getIndices: async (): Promise<MarketIndex[]> => {
    const { data } = await apiClient.get<MarketIndex[]>("/market/indices");
    return data;
  },
};
