export interface IncomeStatementItem {
  period_year: number;
  period_type: string;
  period_quarter: number | null;
  revenue_cr: number | null;
  ebitda_cr: number | null;
  ebitda_margin_pct: number | null;
  pat_cr: number | null;
  net_profit_margin_pct: number | null;
  eps_basic: number | null;
  eps_diluted: number | null;
  dividend_per_share: number | null;
}

export interface BalanceSheetItem {
  period_year: number;
  period_type: string;
  total_assets_cr: number | null;
  shareholders_equity_cr: number | null;
  long_term_debt_cr: number | null;
  short_term_debt_cr: number | null;
  cash_cr: number | null;
  receivables_cr: number | null;
  inventories_cr: number | null;
}

export interface CashFlowItem {
  period_year: number;
  period_type: string;
  cfo_cr: number | null;
  cfi_cr: number | null;
  cff_cr: number | null;
  capex_cr: number | null;
  free_cash_flow_cr: number | null;
}

export interface KeyRatioItem {
  period_year: number;
  period_type: string;
  roe_pct: number | null;
  roce_pct: number | null;
  roa_pct: number | null;
  ebitda_margin_pct: number | null;
  net_profit_margin_pct: number | null;
  pe_ratio: number | null;
  pb_ratio: number | null;
  ev_ebitda: number | null;
  debt_equity_ratio: number | null;
  current_ratio: number | null;
  interest_coverage: number | null;
  revenue_growth_pct: number | null;
  pat_growth_pct: number | null;
  cash_conversion_cycle: number | null;
}

export interface FinancialSummary {
  company_id: string;
  income_statements: IncomeStatementItem[];
  balance_sheets: BalanceSheetItem[];
  cash_flows: CashFlowItem[];
  key_ratios: KeyRatioItem[];
}
