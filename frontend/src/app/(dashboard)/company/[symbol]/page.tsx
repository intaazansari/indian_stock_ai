import type { Metadata } from "next";
import { ExecutiveSummaryCard } from "@/components/ai/ExecutiveSummary";
import { QualityScoreCard } from "@/components/company/QualityScoreCard";
import { PriceChart } from "@/components/company/PriceChart";
import { ShareholdingCard } from "@/components/company/ShareholdingCard";

interface CompanyPageProps {
  params: Promise<{ symbol: string }>;
}

export async function generateMetadata({ params }: CompanyPageProps): Promise<Metadata> {
  const { symbol } = await params;
  return {
    title: symbol.toUpperCase(),
    description: `Fundamental analysis and AI insights for ${symbol.toUpperCase()}`,
  };
}

export default async function CompanyPage({ params }: CompanyPageProps) {
  const { symbol } = await params;
  const upperSymbol = symbol.toUpperCase();

  return (
    <div className="space-y-6">
      {/* Full-width price chart */}
      <PriceChart symbol={upperSymbol} />

      {/* Two-column: AI summary + quality score */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column — AI Summary (2/3 width) */}
        <div className="lg:col-span-2 space-y-6">
          <ExecutiveSummaryCard symbol={upperSymbol} />
        </div>

        {/* Right Column — Quality Score + Shareholding (1/3 width) */}
        <div className="space-y-6">
          <QualityScoreCard symbol={upperSymbol} />
          <ShareholdingCard symbol={upperSymbol} />
        </div>
      </div>
    </div>
  );
}
