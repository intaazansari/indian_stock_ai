"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown, BarChart2 } from "lucide-react";
import { companiesApi } from "@/lib/api/companies";
import type { PricePoint } from "@/types/company";

type Period = "1mo" | "3mo" | "6mo" | "1y" | "3y" | "5y";

const PERIODS: { label: string; value: Period }[] = [
  { label: "1M", value: "1mo" },
  { label: "3M", value: "3mo" },
  { label: "6M", value: "6mo" },
  { label: "1Y", value: "1y" },
  { label: "3Y", value: "3y" },
  { label: "5Y", value: "5y" },
];

function formatPrice(v: number) {
  return `₹${v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Compact Y-axis label — keeps the axis narrow on mobile */
function formatYAxis(v: number) {
  if (v >= 1_00_000) return `₹${(v / 1_00_000).toFixed(1)}L`;
  if (v >= 10_000)   return `₹${(v / 1_000).toFixed(1)}K`;
  return `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function formatVolume(v: number) {
  if (v >= 1_00_00_000) return `${(v / 1_00_00_000).toFixed(2)}Cr`;
  if (v >= 1_00_000) return `${(v / 1_00_000).toFixed(2)}L`;
  return v.toLocaleString("en-IN");
}

function formatXAxis(date: string, period: Period) {
  const d = new Date(date);
  if (period === "1mo" || period === "3mo") {
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  }
  return d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

// Reduce x-axis tick density based on period
function tickInterval(length: number, period: Period) {
  if (period === "1mo") return Math.max(1, Math.floor(length / 5));
  if (period === "3mo") return Math.max(1, Math.floor(length / 6));
  if (period === "6mo") return Math.max(1, Math.floor(length / 6));
  if (period === "1y") return Math.max(1, Math.floor(length / 8));
  return Math.max(1, Math.floor(length / 8));
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: { value: number; payload: PricePoint }[];
  label?: string;
  isPositive: boolean;
}

function CustomTooltip({ active, payload, label, isPositive }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</p>
      <p className={`font-bold text-sm ${isPositive ? "text-emerald-600" : "text-red-500"}`}>
        {formatPrice(point.close)}
      </p>
      <div className="mt-1 space-y-0.5 text-gray-500 dark:text-gray-400">
        <p>O: {formatPrice(point.open)}  H: {formatPrice(point.high)}</p>
        <p>L: {formatPrice(point.low)}  Vol: {formatVolume(point.volume)}</p>
      </div>
    </div>
  );
}

interface PriceChartProps {
  symbol: string;
}

export function PriceChart({ symbol }: PriceChartProps) {
  const [period, setPeriod] = useState<Period>("1y");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["price-history", symbol, period],
    queryFn: () => companiesApi.getPriceHistory(symbol, period),
    staleTime: 5 * 60_000,
    retry: 1,
  });

  const first = data?.[0]?.close ?? 0;
  const last = data?.[data.length - 1]?.close ?? 0;
  const change = last - first;
  const changePct = first > 0 ? (change / first) * 100 : 0;
  const isPositive = change >= 0;

  const colorStroke = isPositive ? "#10b981" : "#ef4444";
  const colorFill = isPositive ? "#10b981" : "#ef4444";

  // 52-week stats (from 1y data regardless of selected period)
  const { data: yearData } = useQuery({
    queryKey: ["price-history", symbol, "1y"],
    queryFn: () => companiesApi.getPriceHistory(symbol, "1y"),
    staleTime: 5 * 60_000,
    retry: 1,
  });
  const week52High = yearData ? Math.max(...yearData.map((p) => p.high)) : null;
  const week52Low  = yearData ? Math.min(...yearData.map((p) => p.low))  : null;

  const interval = data ? tickInterval(data.length, period) : 1;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 sm:p-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Price Chart</span>
          </div>
          {!isLoading && data?.length && (
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-1">
              <span className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatPrice(last)}
              </span>
              <span
                className={`flex items-center gap-1 text-sm font-medium ${
                  isPositive ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400"
                }`}
              >
                {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                {isPositive ? "+" : ""}
                {formatPrice(change)} ({isPositive ? "+" : ""}{changePct.toFixed(2)}%)
              </span>
              <span className="text-xs text-gray-400 dark:text-gray-500 hidden sm:inline">
                {PERIODS.find((p) => p.value === period)?.label}
              </span>
            </div>
          )}
        </div>

        {/* Period selector */}
        <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-2.5 py-1.5 min-h-[2rem] text-xs font-medium rounded-md transition-all ${
                period === p.value
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart area */}
      {isLoading && (
        <div className="h-56 flex items-center justify-center">
          <div className="flex gap-1.5">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600 animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
        </div>
      )}

      {isError && (
        <div className="h-56 flex items-center justify-center text-sm text-gray-400 dark:text-gray-500">
          Price data unavailable
        </div>
      )}

      {!isLoading && !isError && data?.length && (
        <>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`gradient-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colorFill} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={colorFill} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="currentColor"
                className="text-gray-100 dark:text-gray-800"
                vertical={false}
              />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "currentColor" }}
                className="text-gray-400 dark:text-gray-500"
                tickLine={false}
                axisLine={false}
                interval={interval}
                tickFormatter={(v) => formatXAxis(v, period)}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "currentColor" }}
                className="text-gray-400 dark:text-gray-500"
                tickLine={false}
                axisLine={false}
                width={56}
                tickFormatter={formatYAxis}
                domain={["auto", "auto"]}
              />
              <Tooltip
                content={<CustomTooltip isPositive={isPositive} />}
                cursor={{ stroke: colorStroke, strokeWidth: 1, strokeDasharray: "4 2" }}
                allowEscapeViewBox={{ x: false, y: true }}
                offset={8}
              />
              <Area
                type="monotone"
                dataKey="close"
                stroke={colorStroke}
                strokeWidth={2}
                fill={`url(#gradient-${symbol})`}
                dot={false}
                activeDot={{ r: 4, fill: colorStroke, strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>

          {/* 52W stats footer */}
          {week52High && week52Low && (
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
              <div className="text-center">
                <p className="text-xs text-gray-400 dark:text-gray-500">52W Low</p>
                <p className="text-sm font-semibold text-red-500 dark:text-red-400">
                  {formatPrice(week52Low)}
                </p>
              </div>
              {/* progress bar */}
              <div className="flex-1 mx-4">
                <div className="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-red-400 to-emerald-500 rounded-full"
                    style={{
                      width: `${Math.min(100, Math.max(0, ((last - week52Low) / (week52High - week52Low)) * 100))}%`,
                    }}
                  />
                </div>
                <p className="text-center text-xs text-gray-400 mt-0.5">52-week range</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-gray-400 dark:text-gray-500">52W High</p>
                <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                  {formatPrice(week52High)}
                </p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
