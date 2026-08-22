import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable React strict mode for better debugging
  reactStrictMode: true,

  // standalone output only for Docker — Vercel uses its own optimised output
  ...(process.env.DOCKER_BUILD === "true" ? { output: "standalone" } : {}),

  // Image optimisation — allow BSE/NSE logo domains
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.bseindia.com" },
      { protocol: "https", hostname: "**.nseindia.com" },
    ],
  },

  // API proxy — routes all backend calls through Next.js to avoid CORS.
  // The browser always calls the same origin (valuepilotage.com); Next.js
  // server-side proxies to the backend URL.
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${apiUrl}/health`,
      },
    ];
  },

  // Experimental: Partial pre-rendering for dashboard pages
  experimental: {
    ppr: false, // Enable when Next.js 15 PPR is stable
  },
};

export default nextConfig;
