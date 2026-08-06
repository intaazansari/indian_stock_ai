import type { Metadata } from "next";
import { ValuationTab } from "@/components/company/tabs/ValuationTab";

interface Props { params: Promise<{ symbol: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { symbol } = await params;
  return { title: `${symbol.toUpperCase()} · Valuation` };
}
export default async function ValuationPage({ params }: Props) {
  const { symbol } = await params;
  return <ValuationTab symbol={symbol.toUpperCase()} />;
}
