"use client";

/**
 * BackendWakeupBanner
 *
 * Polls the backend /health endpoint every 10 s when it is unreachable
 * (Render free tier spins down after 15 min of inactivity).
 *
 * Behaviour:
 *  - Invisible while backend is healthy.
 *  - Shows an amber banner with a spinner once ANY request fails.
 *  - The moment health returns OK it invalidates the entire TanStack Query
 *    cache so every component auto-refetches without the user clicking anything.
 */

import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";

async function pingHealth() {
  // /health is proxied by Next.js rewrite to the backend — same origin, no CORS.
  const { data } = await axios.get("/health", { timeout: 20_000 });
  return data as { status: string };
}

export function BackendWakeupBanner() {
  const queryClient = useQueryClient();
  const wasDownRef = useRef(false);
  // Only show the banner after 2 consecutive failures to avoid blips.
  const FAILURE_THRESHOLD = 2;

  const { isError, isSuccess, isFetching, failureCount } = useQuery({
    queryKey: ["__backend_health__"],
    queryFn: pingHealth,
    // Poll every 10 s while the backend is unreachable; stop when healthy.
    refetchInterval: (query) =>
      query.state.status === "error" ? 10_000 : false,
    // Retry once before declaring the backend truly down.
    retry: 1,
    retryDelay: 5_000,
    // Always treat as stale so it refetches on window focus too.
    staleTime: 0,
    gcTime: 0,
    refetchOnWindowFocus: true,
  });

  // Track whether we have ever seen confirmed failures in this session.
  useEffect(() => {
    if (failureCount >= FAILURE_THRESHOLD) {
      wasDownRef.current = true;
    }
  }, [failureCount]);

  // When backend comes back online, invalidate everything so components reload.
  useEffect(() => {
    if (isSuccess && wasDownRef.current && !isFetching) {
      wasDownRef.current = false;
      // Invalidate all queries except the health check itself.
      queryClient.invalidateQueries({
        predicate: (q) => q.queryKey[0] !== "__backend_health__",
      });
    }
  }, [isSuccess, isFetching, queryClient]);

  // Only show after confirmed sustained failure (not a single transient blip).
  if (!isError || failureCount < FAILURE_THRESHOLD) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[9999] flex items-center justify-center gap-2.5 bg-amber-50 dark:bg-amber-950 border-b border-amber-200 dark:border-amber-800 px-4 py-2.5 text-sm text-amber-800 dark:text-amber-200 shadow-sm">
      {/* Spinner */}
      <svg
        className="w-4 h-4 animate-spin shrink-0"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      <span>
        Backend is starting up (Render free tier) — data will load automatically
        once ready. Retrying every 10 s…
      </span>
    </div>
  );
}
