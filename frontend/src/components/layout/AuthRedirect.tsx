"use client";

import Link from "next/link";
import { useAuthStore } from "@/stores/useAuthStore";

export function LandingNavActions() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (isAuthenticated) {
    return (
      <Link
        href="/dashboard"
        className="text-sm bg-gray-900 dark:bg-white text-white dark:text-gray-900 px-4 py-2 rounded-lg font-medium hover:opacity-90 transition-opacity"
      >
        Go to Dashboard
      </Link>
    );
  }

  return (
    <>
      <Link
        href="/login"
        className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
      >
        Sign in
      </Link>
      <Link
        href="/signup"
        className="text-sm bg-gray-900 dark:bg-white text-white dark:text-gray-900 px-4 py-2 rounded-lg font-medium hover:opacity-90 transition-opacity"
      >
        Get started
      </Link>
    </>
  );
}
