import { apiClient } from "./client";
import type { Company, CompanySearchResult, PeerCompany } from "@/types/company";
import type { PaginatedResponse } from "./types";

export const companiesApi = {
  getBySymbol: async (symbol: string): Promise<Company> => {
    const { data } = await apiClient.get<Company>(`/companies/${symbol}`);
    return data;
  },

  getPeers: async (symbol: string): Promise<PeerCompany[]> => {
    const { data } = await apiClient.get<PeerCompany[]>(`/companies/${symbol}/peers`);
    return data;
  },

  search: async (
    query: string,
    page = 1,
    pageSize = 10
  ): Promise<PaginatedResponse<CompanySearchResult>> => {
    const { data } = await apiClient.get<PaginatedResponse<CompanySearchResult>>("/search", {
      params: { q: query, page, page_size: pageSize },
    });
    return data;
  },
};
