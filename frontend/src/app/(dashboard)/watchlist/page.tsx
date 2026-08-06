"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { BookMarked, Trash2, TrendingUp, ExternalLink } from "lucide-react";
import { watchlistApi } from "@/lib/api/watchlist";
import { useAuthStore } from "@/stores/useAuthStore";
import { formatCr } from "@/lib/utils";

export default function WatchlistPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const queryClient = useQueryClient();

  // Redirect guests to login
  useEffect(() => {
    if (!isAuthenticated) router.push("/login");
  }, [isAuthenticated, router]);

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["watchlist"],
    queryFn: watchlistApi.list,
    enabled: isAuthenticated,
  });

  const removeMutation = useMutation({
    mutationFn: (companyId: string) => watchlistApi.remove(companyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
  });

  if (!isAuthenticated) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Watchlist</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Companies you&apos;re tracking
          </p>
        </div>
        <Link
          href="/dashboard"
          className="text-sm px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
        >
          + Add companies
        </Link>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 skeleton rounded-xl" />
          ))}
        </div>
      )}

      {!isLoading && items.length === 0 && (
        <div className="py-20 text-center rounded-xl border border-dashed border-gray-200 dark:border-gray-800">
          <BookMarked className="w-10 h-10 text-gray-200 dark:text-gray-800 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-gray-400 mb-4">Your watchlist is empty</p>
          <Link
            href="/dashboard"
            className="text-sm text-brand-600 hover:underline"
          >
            Browse companies to add →
          </Link>
        </div>
      )}

      {!isLoading && items.length > 0 && (
        <div className="rounded-xl border border-gray-100 dark:border-gray-900 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-900 bg-gray-50 dark:bg-gray-900/50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Company</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden sm:table-cell">Sector</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Market Cap</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">CMP</th>
                <th className="px-4 py-3 w-20"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50 dark:divide-gray-900">
              {items.map((item) => (
                <tr
                  key={item.id}
                  className="hover:bg-gray-50 dark:hover:bg-gray-900/50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/company/${item.nse_symbol}`}
                      className="flex items-center gap-2 group"
                    >
                      <div>
                        <div className="font-semibold text-gray-900 dark:text-white font-mono text-xs">
                          {item.nse_symbol}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[180px]">
                          {item.name}
                        </div>
                      </div>
                      <ExternalLink className="w-3 h-3 text-gray-300 dark:text-gray-700 group-hover:text-brand-500 transition-colors" />
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400 hidden sm:table-cell text-xs">
                    {item.sector ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                    {item.market_cap_cr != null ? formatCr(item.market_cap_cr) : "—"}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-gray-900 dark:text-white">
                    {item.cmp != null ? `₹${Number(item.cmp).toFixed(0)}` : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => removeMutation.mutate(item.company_id)}
                      disabled={removeMutation.isPending}
                      className="p-1.5 rounded-lg text-gray-300 dark:text-gray-700 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      title="Remove from watchlist"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
