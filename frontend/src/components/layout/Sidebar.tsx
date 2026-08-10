"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  BookMarked,
  BarChart3,
  Search,
  TrendingUp,
  Brain,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Discover" },
  { href: "/screener", icon: Search, label: "Screener" },
  { href: "/watchlist", icon: BookMarked, label: "Watchlist" },
  { href: "/portfolio", icon: TrendingUp, label: "Portfolio" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex flex-col w-56 shrink-0 bg-white dark:bg-gray-950 border-r border-gray-100 dark:border-gray-900 h-full">
      {/* Logo */}
      <Link
        href="/"
        className="flex items-center gap-2.5 px-4 h-16 border-b border-gray-100 dark:border-gray-900 hover:bg-gray-50 dark:hover:bg-gray-900/50 transition-colors"
      >
        <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
          <Brain className="w-4 h-4 text-white" />
        </div>
        <span className="font-semibold text-gray-900 dark:text-white text-sm">ValuePilotage</span>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors",
                isActive
                  ? "bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-white font-medium"
                  : "text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-900 hover:text-gray-800 dark:hover:text-gray-200"
              )}
            >
              <item.icon className="w-4 h-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-2 pb-4">
        <Link
          href="/settings"
          className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
        >
          <Settings className="w-4 h-4" />
          Settings
        </Link>
      </div>
    </aside>
  );
}
