"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, User, Brain } from "lucide-react";
import { SearchBar } from "./SearchBar";
import { useAuthStore } from "@/stores/useAuthStore";

export function Navbar() {
  const router = useRouter();
  const { user, isAuthenticated, clearAuth } = useAuthStore();

  const handleLogout = () => {
    clearAuth();
    router.push("/");
  };

  return (
    <header className="h-16 border-b border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 flex items-center px-4 sm:px-6 gap-3 shrink-0">
      {/* Logo — only visible on mobile (sidebar hidden below lg) */}
      <Link
        href="/dashboard"
        className="lg:hidden flex items-center gap-2 shrink-0"
      >
        <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
          <Brain className="w-4 h-4 text-white" />
        </div>
        <span className="font-semibold text-gray-900 dark:text-white text-sm">StockSage AI</span>
      </Link>

      <div className="flex-1 max-w-md">
        <SearchBar />
      </div>

      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        {isAuthenticated && user ? (
          <>
            <span className="hidden sm:block text-sm text-gray-600 dark:text-gray-400 truncate max-w-[140px]">
              {user.full_name || user.email}
            </span>
            <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900 flex items-center justify-center shrink-0">
              <User className="w-4 h-4 text-brand-600 dark:text-brand-400" />
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </>
        ) : (
          <>
            <Link
              href="/login"
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/signup"
              className="text-sm px-3 py-1.5 rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-medium hover:opacity-90 transition-opacity whitespace-nowrap"
            >
              Get started
            </Link>
          </>
        )}
      </div>
    </header>
  );
}
