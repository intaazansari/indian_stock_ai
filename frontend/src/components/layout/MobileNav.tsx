"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  LayoutDashboard,
  Search,
  BookMarked,
  TrendingUp,
  Settings,
  Info,
  MoreHorizontal,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/",          icon: Home,            label: "Home"      },
  { href: "/dashboard", icon: LayoutDashboard, label: "Discover"  },
  { href: "/screener",  icon: Search,          label: "Screener"  },
  { href: "/watchlist", icon: BookMarked,      label: "Watchlist" },
  { href: "/portfolio", icon: TrendingUp,      label: "Portfolio" },
];

// Secondary pages live behind "More" — six+ tabs don't fit on small phones.
const MORE_ITEMS = [
  { href: "/about",    icon: Info,     label: "About"    },
  { href: "/settings", icon: Settings, label: "Settings" },
];

const tabClass = (isActive: boolean) =>
  cn(
    "flex-1 flex flex-col items-center justify-center py-2.5 gap-1 text-[10px] font-medium transition-colors",
    isActive
      ? "text-brand-600 dark:text-brand-400"
      : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
  );

export function MobileNav() {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const isMoreActive = MORE_ITEMS.some((item) => item.href === pathname);

  useEffect(() => {
    setMoreOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!moreOpen) return;
    const close = (e: PointerEvent) => {
      if (!moreRef.current?.contains(e.target as Node)) setMoreOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [moreOpen]);

  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-gray-950 border-t border-gray-100 dark:border-gray-900 flex">
      {NAV_ITEMS.map((item) => {
        const isActive = pathname === item.href;
        return (
          <Link key={item.href} href={item.href} className={tabClass(isActive)}>
            <item.icon className={cn("w-5 h-5", isActive && "stroke-[2.5]")} />
            {item.label}
          </Link>
        );
      })}

      <div ref={moreRef} className="relative flex-1 flex">
        <button
          type="button"
          onClick={() => setMoreOpen((open) => !open)}
          aria-expanded={moreOpen}
          aria-haspopup="menu"
          className={tabClass(isMoreActive || moreOpen)}
        >
          <MoreHorizontal className={cn("w-5 h-5", (isMoreActive || moreOpen) && "stroke-[2.5]")} />
          More
        </button>

        {moreOpen && (
          <div
            role="menu"
            className="absolute bottom-full right-2 mb-2 w-44 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-950 shadow-lg py-1.5"
          >
            {MORE_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  role="menuitem"
                  className={cn(
                    "flex items-center gap-3 px-4 py-2.5 text-sm transition-colors",
                    isActive
                      ? "text-brand-600 dark:text-brand-400 font-medium"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900"
                  )}
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </nav>
  );
}
