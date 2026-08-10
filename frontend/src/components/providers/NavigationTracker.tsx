"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

/**
 * Silently tracks pathname changes at the dashboard level.
 * When the user enters the /company/ section from a non-company page,
 * saves the previous URL to sessionStorage so the Back button can
 * jump directly back instead of stepping through every tab visited.
 */
export function NavigationTracker() {
  const pathname = usePathname();
  const prevRef = useRef<string | null>(null);

  useEffect(() => {
    const prev = prevRef.current;
    if (
      prev !== null &&
      !prev.startsWith("/company/") &&
      pathname.startsWith("/company/")
    ) {
      sessionStorage.setItem("company_back_url", prev);
    }
    prevRef.current = pathname;
  }, [pathname]);

  return null;
}
