"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { companiesApi } from "@/lib/api/companies";
import { cn, formatCr } from "@/lib/utils";

interface SearchBarProps {
  size?: "default" | "large";
}

export function SearchBar({ size = "default" }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const { data, isLoading } = useQuery({
    queryKey: ["search", query],
    queryFn: () => companiesApi.search(query, 1, 8),
    enabled: query.length >= 1,
    staleTime: 30_000,
  });

  const results = data?.items ?? [];

  useEffect(() => {
    setIsOpen(query.length >= 1 && (isLoading || results.length > 0));
  }, [query, isLoading, results.length]);

  const handleSelect = (symbol: string) => {
    router.push(`/company/${symbol}`);
    setQuery("");
    setIsOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      setQuery("");
      setIsOpen(false);
    }
    if (e.key === "Enter" && results.length > 0) {
      const first = results[0];
      if (first.nse_symbol) handleSelect(first.nse_symbol);
    }
  };

  return (
    <div className="relative">
      {/* Input */}
      <div
        className={cn(
          "flex items-center gap-2 rounded-lg border bg-white dark:bg-gray-900 transition-colors",
          isOpen
            ? "border-brand-300 dark:border-brand-700 ring-2 ring-brand-100 dark:ring-brand-900"
            : "border-gray-200 dark:border-gray-800",
          size === "large" ? "px-4 py-3" : "px-3 py-2"
        )}
      >
        <Search className={cn("shrink-0 text-gray-400", size === "large" ? "w-5 h-5" : "w-4 h-4")} />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => query.length >= 1 && setIsOpen(true)}
          placeholder={size === "large" ? "Search by company name, NSE symbol…" : "Search companies…"}
          className={cn(
            "flex-1 bg-transparent outline-none text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500",
            size === "large" ? "text-base" : "text-sm"
          )}
        />
        {query && (
          <button onClick={() => { setQuery(""); setIsOpen(false); }}>
            <X className="w-3.5 h-3.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" />
          </button>
        )}
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 shadow-elevated z-50 overflow-hidden">
          {isLoading && (
            <div className="px-4 py-3 text-sm text-gray-400">Searching…</div>
          )}
          {!isLoading && results.length === 0 && query.length >= 1 && (
            <div className="px-4 py-3 text-sm text-gray-400">
              No results for &ldquo;{query}&rdquo;
            </div>
          )}
          {results.map((company) => (
            <button
              key={company.id}
              onClick={() => company.nse_symbol && handleSelect(company.nse_symbol)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-left border-b last:border-0 border-gray-50 dark:border-gray-800/50"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {company.name}
                  </span>
                  {company.nse_symbol && (
                    <span className="text-xs font-mono text-brand-600 dark:text-brand-400">
                      {company.nse_symbol}
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                  {company.sector}
                </div>
              </div>
              {company.market_cap_cr && (
                <span className="text-xs text-gray-400 dark:text-gray-500 shrink-0 ml-4">
                  {formatCr(company.market_cap_cr)}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
