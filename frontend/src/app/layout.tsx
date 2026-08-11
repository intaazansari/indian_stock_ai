import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { GoogleAnalytics } from "@next/third-parties/google";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { BackendWakeupBanner } from "@/components/providers/BackendWakeupBanner";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: {
    default: "ValuePilotage — Indian Stock Research",
    template: "%s | ValuePilotage",
  },
  description:
    "AI-powered Indian stock fundamental analysis. Understand businesses, not just data.",
  keywords: ["Indian stocks", "fundamental analysis", "equity research", "NSE", "BSE"],
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: "https://valuepilotage.com",
    siteName: "ValuePilotage",
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
          <QueryProvider>
            <BackendWakeupBanner />
            {children}
          </QueryProvider>
        </ThemeProvider>
        <GoogleAnalytics gaId="G-J62F8KGPEJ" />
      </body>
    </html>
  );
}
