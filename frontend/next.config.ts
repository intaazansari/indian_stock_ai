import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable React strict mode for better debugging
  reactStrictMode: true,

  // Required for Docker production builds (copies only necessary files)
  output: "standalone",

  // Image optimisation — allow BSE/NSE logo domains
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.bseindia.com" },
      { protocol: "https", hostname: "**.nseindia.com" },
    ],
  },

  // API proxy — avoids CORS issues in development
  // In production, nginx handles this
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },

  // Experimental: Partial pre-rendering for dashboard pages
  experimental: {
    ppr: false, // Enable when Next.js 15 PPR is stable
  },
};

export default nextConfig;
