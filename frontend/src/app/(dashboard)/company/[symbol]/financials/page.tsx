import type { Metadata } from "next";
import { FinancialsTab } from "@/components/company/tabs/FinancialsTab";

interface Props { params: Promise<{ symbol: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { symbol } = await params;
  return { title: `${symbol.toUpperCase()} · Financials` };
}

export default async function FinancialsPage({ params }: Props) {
  const { symbol } = await params;
  return <FinancialsTab symbol={symbol.toUpperCase()} />;
}
