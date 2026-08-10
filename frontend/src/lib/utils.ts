import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a number in Indian notation (₹ Cr, ₹ L, etc.)
 */
function toNum(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "string" ? parseFloat(value) : value;
  return isNaN(n) ? null : n;
}

export function formatCr(value: string | number | null | undefined, decimals = 0): string {
  const n = toNum(value);
  if (n === null) return "—";
  if (Math.abs(n) >= 1_00_000) {
    return `₹${(n / 1_00_000).toFixed(1)}L Cr`;
  }
  if (Math.abs(n) >= 1_000) {
    return `₹${(n / 1_000).toFixed(1)}K Cr`;
  }
  return `₹${n.toFixed(decimals)} Cr`;
}

export function formatNumber(value: string | number | null | undefined, decimals = 1): string {
  const n = toNum(value);
  if (n === null) return "—";
  return n.toFixed(decimals);
}

export function formatPercent(value: string | number | null | undefined, decimals = 1): string {
  const n = toNum(value);
  if (n === null) return "—";
  return `${n.toFixed(decimals)}%`;
}

/**
 * Formats an ISO date string as a relative "X ago" label, or a short date if older.
 */
export function formatUpdatedAt(dateStr: string): string {
  const date = new Date(dateStr);
  const diffMs = Date.now() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return "yesterday";
  if (diffDays < 30) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function formatMultiple(value: string | number | null | undefined, decimals = 1): string {
  const n = toNum(value);
  if (n === null) return "—";
  return `${n.toFixed(decimals)}x`;
}

/**
 * Returns 'positive' | 'negative' | 'neutral' class name based on value sign.
 */
export function getValueClass(value: string | number | null | undefined): string {
  const n = toNum(value);
  if (n === null) return "neutral";
  if (n > 0) return "positive";
  if (n < 0) return "negative";
  return "neutral";
}

/**
 * Returns a colour for a Quality Score (0-10).
 */
export function getScoreColor(score: number): string {
  if (score >= 8) return "text-green-600 dark:text-green-400";
  if (score >= 6) return "text-brand-600 dark:text-brand-400";
  if (score >= 4) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

export function getScoreBg(score: number): string {
  if (score >= 8) return "bg-green-50 dark:bg-green-950 border-green-100 dark:border-green-900";
  if (score >= 6) return "bg-brand-50 dark:bg-brand-950 border-brand-100 dark:border-brand-900";
  if (score >= 4) return "bg-yellow-50 dark:bg-yellow-950 border-yellow-100 dark:border-yellow-900";
  return "bg-red-50 dark:bg-red-950 border-red-100 dark:border-red-900";
}

export function getRiskColor(level: string): string {
  switch (level) {
    case "low": return "text-green-600 dark:text-green-400";
    case "medium": return "text-yellow-600 dark:text-yellow-400";
    case "high": return "text-orange-600 dark:text-orange-400";
    case "critical": return "text-red-600 dark:text-red-400";
    default: return "text-gray-500";
  }
}
