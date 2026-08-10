import { CompanyHeader } from "@/components/company/CompanyHeader";
import { CompanyTabNav } from "@/components/company/CompanyTabNav";

interface CompanyLayoutProps {
  children: React.ReactNode;
  params: Promise<{ symbol: string }>;
}

export default async function CompanyLayout({ children, params }: CompanyLayoutProps) {
  const { symbol } = await params;
  const upperSymbol = symbol.toUpperCase();

  return (
    <div className="space-y-6">
      <CompanyHeader symbol={upperSymbol} />
      <CompanyTabNav symbol={upperSymbol} />
      {children}
    </div>
  );
}
