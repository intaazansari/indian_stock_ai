import type { Metadata } from "next";
import { ResearchTab } from "@/components/company/tabs/ResearchTab";

interface Props { params: Promise<{ symbol: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { symbol } = await params;
  return { title: `${symbol.toUpperCase()} · Research` };
}
export default async function ResearchPage({ params }: Props) {
  const { symbol } = await params;
  return <ResearchTab symbol={symbol.toUpperCase()} />;
}
