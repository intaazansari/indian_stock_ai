"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const COMPANY_TABS = [
  { label: "Overview",   href: "" },
  { label: "Financials", href: "/financials" },
  { label: "Valuation",  href: "/valuation" },
  { label: "Quality",    href: "/quality" },
  { label: "Risks",      href: "/risks" },
  { label: "Peers",      href: "/peers" },
  { label: "Research",   href: "/research" },
];

interface Props {
  symbol: string;
}

export function CompanyTabNav({ symbol }: Props) {
  const pathname = usePathname();

  return (
    <nav className="flex gap-1 border-b border-gray-100 dark:border-gray-900">
      {COMPANY_TABS.map((tab) => {
        const href = `/company/${symbol}${tab.href}`;
        // Overview tab: exact match; others: starts-with match
        const isActive = tab.href === ""
          ? pathname === `/company/${symbol}`
          : pathname.startsWith(href);

        return (
          <Link
            key={tab.href}
            href={href}
            className={cn(
              "px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
              isActive
                ? "text-gray-900 dark:text-white border-brand-600 dark:border-brand-400"
                : "text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white border-transparent hover:border-gray-300 dark:hover:border-gray-600"
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
