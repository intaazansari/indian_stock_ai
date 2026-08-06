export type SentimentLevel =
  | "very_positive"
  | "positive"
  | "neutral"
  | "negative"
  | "very_negative";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface ScoreItem {
  label: string;
  score: number;
  explanation: string;
}

export interface QualityScoreResponse {
  company_id: string;
  overall_score: number;
  business_quality: ScoreItem;
  financial_health: ScoreItem;
  management_quality: ScoreItem;
  growth_quality: ScoreItem;
  valuation: ScoreItem;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  agent_type: string;
  model_used: string;
  generated_at: string;
}

export interface FinancialInsight {
  title: string;
  insight: string;
  sentiment: SentimentLevel;
  metric_value: string | null;
}

export interface FinancialAnalysisResponse {
  company_id: string;
  period_year: number;
  revenue_trend: string;
  profitability_trend: string;
  balance_sheet_health: string;
  cash_flow_quality: string;
  key_insights: FinancialInsight[];
  red_flags: string[];
  positives: string[];
  agent_type: string;
  model_used: string;
  generated_at: string;
}

export interface RedFlag {
  title: string;
  description: string;
  severity: RiskLevel;
  category: string;
}

export interface RiskAnalysisResponse {
  company_id: string;
  overall_risk_level: RiskLevel;
  red_flags: RedFlag[];
  business_risks: string[];
  financial_risks: string[];
  governance_risks: string[];
  regulatory_risks: string[];
  agent_type: string;
  model_used: string;
  generated_at: string;
}

export interface ValuationAnalysisResponse {
  company_id: string;
  current_pe: number | null;
  sector_median_pe: number | null;
  historical_pe_median: number | null;
  valuation_commentary: string;
  is_overvalued: boolean | null;
  fair_value_estimate: number | null;
  upside_downside_pct: number | null;
  valuation_methodology: string;
  key_assumptions: string[];
  agent_type: string;
  model_used: string;
  generated_at: string;
}

export interface ExecutiveSummaryResponse {
  company_id: string;
  one_liner: string;
  business_story: string;
  investment_case: string;
  key_monitorables: string[];
  quality_score: number;
  valuation_score: number;
  risk_score: number;
  overall_verdict: string;
  agent_type: string;
  model_used: string;
  generated_at: string;
}
