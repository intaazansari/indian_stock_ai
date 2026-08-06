import { apiClient } from "./client";

export interface WatchlistItem {
  id: string;
  company_id: string;
  nse_symbol: string | null;
  name: string | null;
  sector: string | null;
  market_cap_cr: number | null;
  cmp: number | null;
}

export const watchlistApi = {
  list: async (): Promise<WatchlistItem[]> => {
    const { data } = await apiClient.get<WatchlistItem[]>("/watchlist");
    return data;
  },

  add: async (companyId: string): Promise<void> => {
    await apiClient.post(`/watchlist/${companyId}`);
  },

  remove: async (companyId: string): Promise<void> => {
    await apiClient.delete(`/watchlist/${companyId}`);
  },
};
