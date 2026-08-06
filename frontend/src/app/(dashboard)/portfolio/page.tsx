"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { TrendingUp, TrendingDown, Plus, Trash2, X } from "lucide-react";
import { portfolioApi, type AddHoldingPayload } from "@/lib/api/portfolio";
import { useAuthStore } from "@/stores/useAuthStore";
import { formatCr, cn } from "@/lib/utils";

// ── Add Holding Modal ─────────────────────────────────────────────────────────

function AddHoldingModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AddHoldingPayload>({
    symbol: "",
    buy_price: 0,
    quantity: 0,
    buy_date: "",
    notes: "",
  });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: portfolioApi.add,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      onClose();
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail ?? "Failed to add holding");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.symbol.trim()) return setError("Symbol is required");
    if (form.buy_price <= 0) return setError("Buy price must be > 0");
    if (form.quantity <= 0) return setError("Quantity must be > 0");

    mutation.mutate({
      symbol: form.symbol.trim().toUpperCase(),
      buy_price: Number(form.buy_price),
      quantity: Number(form.quantity),
      buy_date: form.buy_date || null,
      notes: form.notes || null,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-950 rounded-xl border border-gray-200 dark:border-gray-800 shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-900">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Add Holding</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                NSE Symbol *
              </label>
              <input
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 uppercase"
                placeholder="e.g. TCS"
                value={form.symbol}
                onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Buy Price (₹) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="3500.00"
                value={form.buy_price || ""}
                onChange={(e) => setForm({ ...form, buy_price: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Quantity *
              </label>
              <input
                type="number"
                step="0.0001"
                min="0.0001"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="10"
                value={form.quantity || ""}
                onChange={(e) => setForm({ ...form, quantity: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Buy Date (optional)
              </label>
              <input
                type="date"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={form.buy_date ?? ""}
                onChange={(e) => setForm({ ...form, buy_date: e.target.value })}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Notes (optional)
              </label>
              <input
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="e.g. Long-term conviction pick"
                value={form.notes ?? ""}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
          </div>

          {error && (
            <p className="text-xs text-red-500">{error}</p>
          )}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex-1 px-4 py-2 text-sm rounded-lg bg-brand-600 text-white font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors"
            >
              {mutation.isPending ? "Adding…" : "Add Holding"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── P&L Badge ─────────────────────────────────────────────────────────────────

function PnLBadge({ value, pct }: { value: number | null; pct: number | null }) {
  if (value === null) return <span className="text-gray-400 text-xs">—</span>;
  const positive = value >= 0;
  return (
    <div className={cn("text-right", positive ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400")}>
      <div className="text-sm font-medium tabular-nums">
        {positive ? "+" : ""}₹{Math.abs(value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
      </div>
      {pct !== null && (
        <div className="text-xs">
          {positive ? "+" : ""}{pct.toFixed(2)}%
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function PortfolioPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const queryClient = useQueryClient();
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) router.push("/login");
  }, [isAuthenticated, router]);

  const { data, isLoading } = useQuery({
    queryKey: ["portfolio"],
    queryFn: portfolioApi.get,
    enabled: isAuthenticated,
  });

  const removeMutation = useMutation({
    mutationFn: portfolioApi.remove,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["portfolio"] }),
  });

  if (!isAuthenticated) return null;

  const holdings = data?.holdings ?? [];
  const overallPositive = (data?.total_gain_loss ?? 0) >= 0;

  return (
    <div className="space-y-6">
      {showModal && <AddHoldingModal onClose={() => setShowModal(false)} />}

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Portfolio</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Track your holdings and unrealised P&amp;L
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Holding
        </button>
      </div>

      {/* ── Summary Cards ── */}
      {data && holdings.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 px-5 py-4">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Total Invested</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white tabular-nums">
              ₹{data.total_invested.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
            </p>
          </div>
          <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 px-5 py-4">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Current Value</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white tabular-nums">
              {data.total_current_value !== null
                ? `₹${data.total_current_value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`
                : "—"}
            </p>
          </div>
          <div className={cn(
            "rounded-xl border px-5 py-4",
            overallPositive
              ? "border-green-100 dark:border-green-900/30 bg-green-50 dark:bg-green-950/20"
              : "border-red-100 dark:border-red-900/30 bg-red-50 dark:bg-red-950/20"
          )}>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Unrealised P&amp;L</p>
            {data.total_gain_loss !== null ? (
              <div className={cn(
                "text-xl font-bold tabular-nums",
                overallPositive ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400"
              )}>
                {overallPositive ? "+" : ""}₹{Math.abs(data.total_gain_loss).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                <span className="text-sm font-normal ml-2">
                  ({overallPositive ? "+" : ""}{data.total_gain_loss_pct?.toFixed(2)}%)
                </span>
              </div>
            ) : (
              <p className="text-xl font-bold text-gray-400">—</p>
            )}
          </div>
        </div>
      )}

      {/* ── Holdings Table ── */}
      <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-900">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
            Holdings {holdings.length > 0 && <span className="text-gray-400 font-normal">({holdings.length})</span>}
          </h2>
        </div>

        {isLoading ? (
          <div className="p-5 space-y-3 animate-pulse">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-14 bg-gray-100 dark:bg-gray-900 rounded" />
            ))}
          </div>
        ) : holdings.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <TrendingUp className="w-10 h-10 text-gray-200 dark:text-gray-800 mx-auto mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              No holdings yet. Add your first stock.
            </p>
            <button
              onClick={() => setShowModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Holding
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 dark:border-gray-900 text-xs text-gray-400 dark:text-gray-500">
                  <th className="px-5 py-3 text-left font-medium">Company</th>
                  <th className="px-4 py-3 text-right font-medium">Qty</th>
                  <th className="px-4 py-3 text-right font-medium">Avg Cost</th>
                  <th className="px-4 py-3 text-right font-medium">CMP</th>
                  <th className="px-4 py-3 text-right font-medium">Invested</th>
                  <th className="px-4 py-3 text-right font-medium">Current</th>
                  <th className="px-4 py-3 text-right font-medium">P&amp;L</th>
                  <th className="px-4 py-3 text-center font-medium">Remove</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => (
                  <tr
                    key={h.id}
                    className="border-b border-gray-50 dark:border-gray-900/50 hover:bg-gray-50 dark:hover:bg-gray-900/30 transition-colors"
                  >
                    <td className="px-5 py-3">
                      <a
                        href={`/company/${h.nse_symbol}`}
                        className="font-medium text-gray-900 dark:text-white hover:text-brand-600 dark:hover:text-brand-400"
                      >
                        {h.nse_symbol}
                      </a>
                      <p className="text-xs text-gray-400 dark:text-gray-500 truncate max-w-[160px]">{h.name}</p>
                      {h.buy_date && (
                        <p className="text-xs text-gray-300 dark:text-gray-600">{h.buy_date}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700 dark:text-gray-300">
                      {h.quantity % 1 === 0 ? h.quantity.toFixed(0) : h.quantity.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700 dark:text-gray-300">
                      ₹{h.buy_price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700 dark:text-gray-300">
                      {h.cmp !== null ? `₹${h.cmp.toLocaleString("en-IN", { maximumFractionDigits: 0 })}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700 dark:text-gray-300">
                      ₹{h.invested_value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700 dark:text-gray-300">
                      {h.current_value !== null
                        ? `₹${h.current_value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <PnLBadge value={h.gain_loss} pct={h.gain_loss_pct} />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => removeMutation.mutate(h.id)}
                        disabled={removeMutation.isPending}
                        className="text-gray-300 dark:text-gray-700 hover:text-red-500 dark:hover:text-red-400 transition-colors disabled:opacity-50"
                        title="Remove holding"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="text-xs text-gray-400 dark:text-gray-600 text-center">
        P&amp;L is unrealised and based on last seeded CMP. Prices update when data is refreshed.
      </p>
    </div>
  );
}
