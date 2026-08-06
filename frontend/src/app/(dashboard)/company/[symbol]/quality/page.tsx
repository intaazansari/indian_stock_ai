import type { Metadata } from "next";
import { QualityTab } from "@/components/company/tabs/QualityTab";

interface Props { params: Promise<{ symbol: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { symbol } = await params;
  return { title: `${symbol.toUpperCase()} · Quality` };
}
export default async function QualityPage({ params }: Props) {
  const { symbol } = await params;
  return <QualityTab symbol={symbol.toUpperCase()} />;
}
