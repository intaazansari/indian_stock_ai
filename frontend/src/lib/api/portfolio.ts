import { apiClient } from "./client";

export interface HoldingItem {
  id: string;
  company_id: string;
  nse_symbol: string;
  name: string;
  sector: string | null;
  buy_price: number;
  quantity: number;
  buy_date: string | null;
  notes: string | null;
  cmp: number | null;
  invested_value: number;
  current_value: number | null;
  gain_loss: number | null;
  gain_loss_pct: number | null;
}

export interface PortfolioSummary {
  total_invested: number;
  total_current_value: number | null;
  total_gain_loss: number | null;
  total_gain_loss_pct: number | null;
  holdings: HoldingItem[];
}

export interface AddHoldingPayload {
  symbol: string;
  buy_price: number;
  quantity: number;
  buy_date?: string | null;
  notes?: string | null;
}

export const portfolioApi = {
  get: async (): Promise<PortfolioSummary> => {
    const { data } = await apiClient.get<PortfolioSummary>("/portfolio");
    return data;
  },

  add: async (payload: AddHoldingPayload): Promise<HoldingItem> => {
    const { data } = await apiClient.post<HoldingItem>("/portfolio", payload);
    return data;
  },

  remove: async (holdingId: string): Promise<void> => {
    await apiClient.delete(`/portfolio/${holdingId}`);
  },
};
