export interface Company {
  id: string;
  name: string;
  nse_symbol: string | null;
  bse_code: string | null;
  isin: string | null;
  sector: string | null;
  industry: string | null;
  market_cap_cr: number | null;
  face_value: number | null;
  cmp: number | null;
  week52_high: number | null;
  week52_low: number | null;
  promoter_holding_pct: number | null;
  fii_holding_pct: number | null;
  dii_holding_pct: number | null;
  public_holding_pct: number | null;
  description: string | null;
  website: string | null;
  founded_year: number | null;
  headquarters: string | null;
  employee_count: number | null;
  updated_at: string | null;
}

export interface CompanySearchResult {
  id: string;
  name: string;
  nse_symbol: string | null;
  bse_code: string | null;
  sector: string | null;
  industry: string | null;
  market_cap_cr: number | null;
  cmp: number | null;
}

export interface PeerCompany {
  id: string;
  name: string;
  nse_symbol: string | null;
  bse_code: string | null;
  sector: string | null;
  industry: string | null;
  market_cap_cr: string | number | null;
  cmp: string | number | null;
  promoter_holding_pct: string | number | null;
  pe_ratio: string | number | null;
  pb_ratio: string | number | null;
  roe_pct: string | number | null;
  roce_pct: string | number | null;
  net_profit_margin_pct: string | number | null;
  debt_equity_ratio: string | number | null;
  revenue_growth_pct: string | number | null;
}
