"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, LayoutDashboard, Search, BookMarked, TrendingUp, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/",          icon: Home,            label: "Home"      },
  { href: "/dashboard", icon: LayoutDashboard, label: "Discover"  },
  { href: "/screener",  icon: Search,          label: "Screener"  },
  { href: "/watchlist", icon: BookMarked,      label: "Watchlist" },
  { href: "/settings",  icon: Settings,        label: "Settings"  },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-gray-950 border-t border-gray-100 dark:border-gray-900 flex">
      {NAV_ITEMS.map((item) => {
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex-1 flex flex-col items-center justify-center py-2.5 gap-1 text-[10px] font-medium transition-colors",
              isActive
                ? "text-brand-600 dark:text-brand-400"
                : "text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            )}
          >
            <item.icon className={cn("w-5 h-5", isActive && "stroke-[2.5]")} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
