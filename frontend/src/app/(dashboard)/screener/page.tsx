"use client";

import { useState, useCallback } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  SlidersHorizontal, ArrowUpDown, ArrowUp, ArrowDown,
  ChevronLeft, ChevronRight, RotateCcw, Search,
} from "lucide-react";
import { screenerApi, type ScreenerFilter, type ScreenerResult, type SortField } from "@/lib/api/screener";
import { cn, formatCr } from "@/lib/utils";

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmt(val: number | null, decimals = 1): string {
  if (val == null) return "—";
  return val.toFixed(decimals);
}

function fmtPct(val: number | null): string {
  if (val == null) return "—";
  return `${val.toFixed(1)}%`;
}

const SORT_LABELS: Record<SortField, string> = {
  market_cap:            "Market Cap",
  pe_ratio:              "P/E",
  pb_ratio:              "P/B",
  roe_pct:               "ROE %",
  roce_pct:              "ROCE %",
  revenue_growth_pct:    "Rev. Growth",
  pat_growth_pct:        "PAT Growth",
  debt_equity_ratio:     "D/E Ratio",
  net_profit_margin_pct: "Net Margin",
  dividend_yield_pct:    "Div. Yield",
};

// Preset filter templates
const PRESETS: Array<{ label: string; filters: Partial<ScreenerFilter> }> = [
  { label: "Quality compounders", filters: { roce_min: 20, roe_min: 15, debt_equity_max: 0.5 } },
  { label: "Value picks",         filters: { pe_max: 20, pb_max: 3, roe_min: 12 } },
  { label: "High growth",         filters: { revenue_growth_min: 15, pat_growth_min: 15 } },
  { label: "Low debt",            filters: { debt_equity_max: 0.3 } },
  { label: "High ROCE",           filters: { roce_min: 25, sort_by: "roce_pct" } },
];

// ── NumInput ─────────────────────────────────────────────────────────────────

function NumInput({
  label, value, onChange, placeholder,
}: {
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</label>
      <input
        type="number"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        placeholder={placeholder ?? "—"}
        className="w-full px-2 py-1.5 text-sm rounded-md border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

const DEFAULT_FILTERS: ScreenerFilter = {
  sort_by: "market_cap",
  sort_order: "desc",
  page: 1,
  page_size: 25,
};

export default function ScreenerPage() {
  const router = useRouter();
  const [filters, setFilters] = useState<ScreenerFilter>(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<ScreenerFilter>(DEFAULT_FILTERS);

  // Load sectors for dropdown
  const { data: sectors = [] } = useQuery({
    queryKey: ["screener-sectors"],
    queryFn: screenerApi.getSectors,
    staleTime: 10 * 60_000,
  });

  // Run screener
  const { data, isFetching } = useQuery({
    queryKey: ["screener", appliedFilters],
    queryFn: () => screenerApi.filter(appliedFilters),
    staleTime: 2 * 60_000,
    placeholderData: (prev) => prev,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = data?.total_pages ?? 1;

  const apply = useCallback(() => {
    setAppliedFilters({ ...filters, page: 1 });
  }, [filters]);

  const reset = () => {
    setFilters(DEFAULT_FILTERS);
    setAppliedFilters(DEFAULT_FILTERS);
  };

  const setPage = (p: number) => {
    const next = { ...appliedFilters, page: p };
    setAppliedFilters(next);
    setFilters(next);
  };

  const toggleSort = (field: SortField) => {
    const next: ScreenerFilter = {
      ...appliedFilters,
      sort_by: field,
      sort_order:
        appliedFilters.sort_by === field && appliedFilters.sort_order === "desc"
          ? "asc"
          : "desc",
      page: 1,
    };
    setFilters(next);
    setAppliedFilters(next);
  };

  const applyPreset = (preset: typeof PRESETS[number]) => {
    const next = { ...DEFAULT_FILTERS, ...preset.filters };
    setFilters(next);
    setAppliedFilters(next);
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex gap-6">
      {/* ── LEFT: Filter panel ───────────────────────────────────────────── */}
      <aside className="w-64 shrink-0 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-brand-600" />
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Filters</h2>
          </div>
          <button
            onClick={reset}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
          >
            <RotateCcw className="w-3 h-3" /> Reset
          </button>
        </div>

        {/* Presets */}
        <div>
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Quick Presets</p>
          <div className="flex flex-col gap-1">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                onClick={() => applyPreset(p)}
                className="text-left text-xs px-3 py-1.5 rounded-lg border border-gray-100 dark:border-gray-900 hover:border-brand-200 hover:bg-brand-50 dark:hover:border-brand-900 dark:hover:bg-brand-950 text-gray-600 dark:text-gray-400 hover:text-brand-700 dark:hover:text-brand-300 transition-all"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Sector */}
        <div>
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Sector</p>
          <select
            value={filters.sector ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, sector: e.target.value || null }))}
            className="w-full px-2 py-1.5 text-sm rounded-md border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">All sectors</option>
            {sectors.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        {/* Valuation */}
        <FilterSection title="Valuation">
          <NumInput label="P/E max"  value={filters.pe_max  ?? null} onChange={(v) => setFilters((f) => ({ ...f, pe_max: v }))}  placeholder="e.g. 25" />
          <NumInput label="P/E min"  value={filters.pe_min  ?? null} onChange={(v) => setFilters((f) => ({ ...f, pe_min: v }))}  placeholder="e.g. 5" />
          <NumInput label="P/B max"  value={filters.pb_max  ?? null} onChange={(v) => setFilters((f) => ({ ...f, pb_max: v }))}  placeholder="e.g. 5" />
        </FilterSection>

        {/* Profitability */}
        <FilterSection title="Profitability">
          <NumInput label="ROCE min (%)" value={filters.roce_min ?? null} onChange={(v) => setFilters((f) => ({ ...f, roce_min: v }))} placeholder="e.g. 15" />
          <NumInput label="ROE min (%)"  value={filters.roe_min  ?? null} onChange={(v) => setFilters((f) => ({ ...f, roe_min: v }))}  placeholder="e.g. 12" />
          <NumInput label="Net margin min (%)" value={filters.net_profit_margin_min ?? null} onChange={(v) => setFilters((f) => ({ ...f, net_profit_margin_min: v }))} placeholder="e.g. 10" />
        </FilterSection>

        {/* Growth */}
        <FilterSection title="Growth (YoY %)">
          <NumInput label="Revenue growth min" value={filters.revenue_growth_min ?? null} onChange={(v) => setFilters((f) => ({ ...f, revenue_growth_min: v }))} placeholder="e.g. 10" />
          <NumInput label="PAT growth min"     value={filters.pat_growth_min    ?? null} onChange={(v) => setFilters((f) => ({ ...f, pat_growth_min: v }))}     placeholder="e.g. 10" />
        </FilterSection>

        {/* Financial Health */}
        <FilterSection title="Financial Health">
          <NumInput label="D/E ratio max"     value={filters.debt_equity_max  ?? null} onChange={(v) => setFilters((f) => ({ ...f, debt_equity_max: v }))}  placeholder="e.g. 1" />
          <NumInput label="Current ratio min" value={filters.current_ratio_min ?? null} onChange={(v) => setFilters((f) => ({ ...f, current_ratio_min: v }))} placeholder="e.g. 1.5" />
        </FilterSection>

        {/* Market Cap */}
        <FilterSection title="Market Cap (₹ Cr)">
          <NumInput label="Min" value={filters.market_cap_min ?? null} onChange={(v) => setFilters((f) => ({ ...f, market_cap_min: v }))} placeholder="e.g. 10000" />
          <NumInput label="Max" value={filters.market_cap_max ?? null} onChange={(v) => setFilters((f) => ({ ...f, market_cap_max: v }))} placeholder="e.g. 500000" />
        </FilterSection>

        {/* Ownership */}
        <FilterSection title="Ownership">
          <NumInput label="Promoter holding min (%)" value={filters.promoter_holding_min ?? null} onChange={(v) => setFilters((f) => ({ ...f, promoter_holding_min: v }))} placeholder="e.g. 50" />
        </FilterSection>

        {/* Apply */}
        <button
          onClick={apply}
          className="w-full py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium transition-colors flex items-center justify-center gap-2"
        >
          <Search className="w-3.5 h-3.5" />
          Apply filters
        </button>
      </aside>

      {/* ── RIGHT: Results ──────────────────────────────────────────────────── */}
      <div className="flex-1 min-w-0 space-y-4">
        {/* Toolbar */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Stock Screener</h1>
            {!isFetching && (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {total} {total === 1 ? "company" : "companies"} match your criteria
              </p>
            )}
          </div>

          {/* Sort dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 dark:text-gray-400">Sort by</span>
            <select
              value={appliedFilters.sort_by}
              onChange={(e) => toggleSort(e.target.value as SortField)}
              className="text-sm px-2 py-1.5 rounded-md border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {(Object.entries(SORT_LABELS) as [SortField, string][]).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
            <button
              onClick={() => toggleSort(appliedFilters.sort_by ?? "market_cap")}
              className="p-1.5 rounded-md border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors"
            >
              {appliedFilters.sort_order === "desc"
                ? <ArrowDown className="w-3.5 h-3.5 text-gray-500" />
                : <ArrowUp className="w-3.5 h-3.5 text-gray-500" />}
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="rounded-xl border border-gray-100 dark:border-gray-900 overflow-hidden bg-white dark:bg-gray-950">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 dark:border-gray-900 bg-gray-50 dark:bg-gray-900/50">
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400 w-48">Company</th>
                  <SortTh field="market_cap"            label="Mkt Cap (Cr)"  current={appliedFilters} onClick={toggleSort} />
                  <SortTh field="pe_ratio"              label="P/E"           current={appliedFilters} onClick={toggleSort} />
                  <SortTh field="pb_ratio"              label="P/B"           current={appliedFilters} onClick={toggleSort} />
                  <SortTh field="roce_pct"              label="ROCE %"        current={appliedFilters} onClick={toggleSort} />
                  <SortTh field="roe_pct"               label="ROE %"         current={appliedFilters} onClick={toggleSort} />
                  <SortTh field="net_profit_margin_pct" label="Net Margin"    current={appliedFilters} onClick={toggleSort} />
                  <SortTh field="revenue_growth_pct"    label="Rev. Growth"   current={appliedFilters} onClick={toggleSort} />
                  <SortTh field="debt_equity_ratio"     label="D/E"           current={appliedFilters} onClick={toggleSort} />
                </tr>
              </thead>
              <tbody>
                {isFetching && items.length === 0 ? (
                  [...Array(8)].map((_, i) => (
                    <tr key={i} className="border-b border-gray-50 dark:border-gray-900">
                      {[...Array(9)].map((_, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 skeleton rounded w-full" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center py-16 text-gray-400 dark:text-gray-500">
                      No companies match the current filters.
                    </td>
                  </tr>
                ) : (
                  items.map((c) => (
                    <ResultRow key={c.id} company={c} />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
            <span>
              Page {appliedFilters.page ?? 1} of {totalPages} · {total} results
            </span>
            <div className="flex items-center gap-1">
              <button
                disabled={(appliedFilters.page ?? 1) <= 1}
                onClick={() => setPage((appliedFilters.page ?? 1) - 1)}
                className="p-1.5 rounded-md border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-900 disabled:opacity-40 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                disabled={(appliedFilters.page ?? 1) >= totalPages}
                onClick={() => setPage((appliedFilters.page ?? 1) + 1)}
                className="p-1.5 rounded-md border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-900 disabled:opacity-40 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function FilterSection({
  title, children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
        {title}
      </p>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function SortTh({
  field, label, current, onClick,
}: {
  field: SortField;
  label: string;
  current: ScreenerFilter;
  onClick: (f: SortField) => void;
}) {
  const isActive = current.sort_by === field;
  return (
    <th
      onClick={() => onClick(field)}
      className="px-4 py-3 text-right font-medium text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-900 dark:hover:text-white transition-colors whitespace-nowrap select-none"
    >
      <span className="inline-flex items-center gap-1 justify-end">
        {label}
        {isActive ? (
          current.sort_order === "desc"
            ? <ArrowDown className="w-3 h-3 text-brand-500" />
            : <ArrowUp className="w-3 h-3 text-brand-500" />
        ) : (
          <ArrowUpDown className="w-3 h-3 opacity-30" />
        )}
      </span>
    </th>
  );
}

function ResultRow({ company: c }: { company: ScreenerResult }) {
  const router = useRouter();
  const symbol = c.nse_symbol;

  return (
    <tr
      onClick={() => symbol && router.push(`/company/${symbol}`)}
      className="border-b border-gray-50 dark:border-gray-900 hover:bg-gray-50 dark:hover:bg-gray-900/50 cursor-pointer transition-colors group"
    >
      {/* Company name */}
      <td className="px-4 py-3">
        <p className="font-medium text-gray-900 dark:text-white group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors text-sm leading-tight">
          {c.name}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          {symbol && (
            <span className="text-xs font-mono text-brand-600 dark:text-brand-400">{symbol}</span>
          )}
          {c.sector && (
            <span className="text-xs text-gray-400 dark:text-gray-500 truncate max-w-[100px]">{c.sector}</span>
          )}
        </div>
      </td>

      {/* Numeric columns */}
      <td className="px-4 py-3 text-right tabular-nums text-gray-700 dark:text-gray-300">
        {c.market_cap_cr ? formatCr(Number(c.market_cap_cr)) : "—"}
      </td>
      <NumCell value={c.pe_ratio}              warn={(v) => v > 50} good={(v) => v < 20 && v > 0} />
      <NumCell value={c.pb_ratio}              warn={(v) => v > 10} good={(v) => v < 3} />
      <NumCell value={c.roce_pct}    pct       good={(v) => v > 20} warn={(v) => v < 10} />
      <NumCell value={c.roe_pct}     pct       good={(v) => v > 15} warn={(v) => v < 8} />
      <NumCell value={c.net_profit_margin_pct} pct good={(v) => v > 15} warn={(v) => v < 5} />
      <NumCell value={c.revenue_growth_pct}    pct good={(v) => v > 15} warn={(v) => v < 0} />
      <NumCell value={c.debt_equity_ratio}         good={(v) => v < 0.5} warn={(v) => v > 2} />
    </tr>
  );
}

function NumCell({
  value, pct = false,
  good, warn,
}: {
  value: number | null;
  pct?: boolean;
  good?: (v: number) => boolean;
  warn?: (v: number) => boolean;
}) {
  if (value == null) {
    return (
      <td className="px-4 py-3 text-right text-gray-300 dark:text-gray-600 tabular-nums">—</td>
    );
  }
  const n = Number(value);           // Decimal fields come back as strings from Python
  if (isNaN(n)) {
    return (
      <td className="px-4 py-3 text-right text-gray-300 dark:text-gray-600 tabular-nums">—</td>
    );
  }
  const isGood = good?.(n);
  const isWarn = warn?.(n);
  return (
    <td
      className={cn(
        "px-4 py-3 text-right tabular-nums font-medium",
        isGood ? "text-emerald-600 dark:text-emerald-400" :
        isWarn ? "text-red-500 dark:text-red-400" :
        "text-gray-700 dark:text-gray-300"
      )}
    >
      {pct ? `${n.toFixed(1)}%` : n.toFixed(1)}
    </td>
  );
}
