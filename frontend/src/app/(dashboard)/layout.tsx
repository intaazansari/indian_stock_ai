import { Sidebar } from "@/components/layout/Sidebar";
import { Navbar } from "@/components/layout/Navbar";
import { MobileNav } from "@/components/layout/MobileNav";
import { NavigationTracker } from "@/components/providers/NavigationTracker";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <div className="flex h-screen bg-[#eef2f7] dark:bg-gray-950 overflow-hidden">
        <Sidebar />
        {/* min-h-0 required so flex-1 children can shrink below content height on iOS */}
        <div className="flex flex-col flex-1 min-w-0 min-h-0">
          <Navbar />
          <main className="flex-1 overflow-y-auto min-h-0">
            <NavigationTracker />
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-24 lg:pb-6">
              {children}
            </div>
          </main>
        </div>
      </div>
      {/* Outside the overflow-hidden flex container so it renders above everything */}
      <MobileNav />
    </>
  );
}
