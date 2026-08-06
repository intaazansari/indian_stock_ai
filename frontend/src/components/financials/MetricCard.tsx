import { cn, getValueClass } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string;
  change?: number;       // YoY change %
  subtext?: string;
  highlight?: boolean;
}

export function MetricCard({ label, value, change, subtext, highlight }: MetricCardProps) {
  const changeClass = change != null ? getValueClass(change) : "neutral";

  return (
    <div
      className={cn(
        "rounded-xl border p-4 bg-white dark:bg-gray-950",
        highlight
          ? "border-brand-200 dark:border-brand-800"
          : "border-gray-100 dark:border-gray-900"
      )}
    >
      <p className="text-xs text-gray-400 dark:text-gray-500 mb-1">{label}</p>
      <p className="text-xl font-bold text-gray-900 dark:text-white tabular-nums">{value}</p>
      {change != null && (
        <div className={cn("flex items-center gap-1 mt-1 text-xs", changeClass)}>
          {change > 0 ? (
            <TrendingUp className="w-3 h-3" />
          ) : change < 0 ? (
            <TrendingDown className="w-3 h-3" />
          ) : (
            <Minus className="w-3 h-3" />
          )}
          <span>{change > 0 ? "+" : ""}{change.toFixed(1)}% YoY</span>
        </div>
      )}
      {subtext && (
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{subtext}</p>
      )}
    </div>
  );
}
