import { useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { analysisApi } from "@/lib/api/analysis";
import type { ExecutiveSummaryResponse, QualityScoreResponse } from "@/types/analysis";

type AgentType = "summary" | "quality" | "financial" | "risk" | "valuation" | "research";

export function useAIAnalysis<T>(symbol: string, agentType: AgentType) {
  return useQuery<T>({
    queryKey: ["analysis", symbol, agentType],
    queryFn: () => analysisApi.getCachedAnalysis(symbol, agentType) as Promise<T>,
    staleTime: 60 * 60 * 1000,   // 1 hour — AI analysis changes rarely
    enabled: Boolean(symbol),
  });
}

export function useExecutiveSummary(symbol: string) {
  return useAIAnalysis<ExecutiveSummaryResponse>(symbol, "summary");
}

export function useQualityScore(symbol: string) {
  return useAIAnalysis<QualityScoreResponse>(symbol, "quality");
}

/**
 * Hook for streaming a fresh AI analysis.
 * Used when user clicks "Refresh Analysis".
 */
export function useStreamAnalysis(symbol: string, agentType: AgentType) {
  const [streamContent, setStreamContent] = useState<string>("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const startStream = useCallback(async () => {
    setIsStreaming(true);
    setStreamContent("");
    setStreamError(null);

    try {
      await analysisApi.streamAnalysis(
        symbol,
        agentType,
        (chunk) => {
          try {
            const parsed = JSON.parse(chunk);
            // Backend yields {"result": {...}} — show a loading indicator
            if (parsed?.result) {
              setStreamContent("Analysis complete. Loading…");
            } else if (parsed?.content) {
              setStreamContent((prev) => prev + parsed.content);
            }
          } catch {
            // raw text chunk
            setStreamContent((prev) => prev + chunk);
          }
        },
        () => {
          setIsStreaming(false);
          // Invalidate cached query so the GET endpoint re-fetches the saved result
          queryClient.invalidateQueries({ queryKey: ["analysis", symbol, agentType] });
        },
        (error) => {
          setStreamError(error.message);
          setIsStreaming(false);
        }
      );
    } catch (err) {
      setStreamError(err instanceof Error ? err.message : "Unknown error");
      setIsStreaming(false);
    }
  }, [symbol, agentType, queryClient]);

  return { streamContent, isStreaming, streamError, startStream };
}
