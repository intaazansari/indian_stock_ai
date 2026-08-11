import { apiClient } from "./client";
import type {
  ExecutiveSummaryResponse,
  FinancialAnalysisResponse,
  QualityScoreResponse,
  RiskAnalysisResponse,
  ValuationAnalysisResponse,
} from "@/types/analysis";

type AgentType =
  | "research"
  | "financial"
  | "quality"
  | "valuation"
  | "risk"
  | "management"
  | "quarterly"
  | "summary";

type AnalysisResponseMap = {
  summary: ExecutiveSummaryResponse;
  quality: QualityScoreResponse;
  financial: FinancialAnalysisResponse;
  risk: RiskAnalysisResponse;
  valuation: ValuationAnalysisResponse;
};

export const analysisApi = {
  getCachedAnalysis: async <T extends AgentType>(
    symbol: string,
    agentType: T
  ): Promise<T extends keyof AnalysisResponseMap ? AnalysisResponseMap[T] : Record<string, unknown>> => {
    const { data } = await apiClient.get(`/companies/${symbol}/analysis/${agentType}`);
    return data;
  },

  /**
   * Stream a fresh AI analysis via SSE.
   * Returns a ReadableStream — connect with EventSource or fetch streaming.
   */
  streamAnalysis: async (
    symbol: string,
    agentType: AgentType,
    onChunk: (chunk: string) => void,
    onDone: () => void,
    onError: (error: Error) => void
  ): Promise<void> => {
    const token = localStorage.getItem("access_token");
    const response = await fetch(
      `/api/v1/companies/${symbol}/analysis/stream`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ agent_type: agentType, force_refresh: true }),
      }
    );

    if (!response.ok) throw new Error(`Stream failed: ${response.status}`);
    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      const lines = text.split("\n").filter((l) => l.startsWith("data: "));

      for (const line of lines) {
        const data = line.replace("data: ", "").trim();
        if (data === "[DONE]") {
          onDone();
          return;
        }
        onChunk(data);
      }
    }
    onDone();
  },
};
