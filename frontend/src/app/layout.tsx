import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { QueryProvider } from "@/components/providers/QueryProvider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: {
    default: "StockSage AI — Indian Stock Research",
    template: "%s | StockSage AI",
  },
  description:
    "AI-powered Indian stock fundamental analysis. Understand businesses, not just data.",
  keywords: ["Indian stocks", "fundamental analysis", "equity research", "NSE", "BSE"],
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: "https://stocksage.ai",
    siteName: "StockSage AI",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          <QueryProvider>{children}</QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
