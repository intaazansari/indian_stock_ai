import type { Metadata } from "next";
import { PeersTab } from "@/components/company/tabs/PeersTab";

interface Props { params: Promise<{ symbol: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { symbol } = await params;
  return { title: `${symbol.toUpperCase()} · Peers` };
}
export default async function PeersPage({ params }: Props) {
  const { symbol } = await params;
  return <PeersTab symbol={symbol.toUpperCase()} />;
}
