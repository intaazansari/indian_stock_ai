import type { Metadata } from "next";
import { RisksTab } from "@/components/company/tabs/RisksTab";

interface Props { params: Promise<{ symbol: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { symbol } = await params;
  return { title: `${symbol.toUpperCase()} · Risks` };
}
export default async function RisksPage({ params }: Props) {
  const { symbol } = await params;
  return <RisksTab symbol={symbol.toUpperCase()} />;
}
