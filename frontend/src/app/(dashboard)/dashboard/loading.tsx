// Shown instantly by Next.js App Router while DashboardHomePage loads
export default function DashboardLoading() {
  return (
    <div className="space-y-8">
      {/* Market overview skeleton */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 p-4 space-y-2">
            <div className="h-3 skeleton rounded w-16" />
            <div className="h-7 skeleton rounded w-24" />
            <div className="h-3 skeleton rounded w-20" />
          </div>
        ))}
      </div>

      {/* Search bar skeleton */}
      <div className="text-center py-8 space-y-4">
        <div className="h-8 skeleton rounded w-72 mx-auto" />
        <div className="h-4 skeleton rounded w-48 mx-auto" />
        <div className="h-12 skeleton rounded-xl w-full max-w-xl mx-auto" />
      </div>

      {/* Popular companies skeleton */}
      <div className="space-y-4">
        <div className="h-3 skeleton rounded w-36" />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {[...Array(12)].map((_, i) => (
            <div key={i} className="rounded-xl border border-gray-100 dark:border-gray-900 p-4 space-y-1.5">
              <div className="h-3 skeleton rounded w-16 mx-auto" />
              <div className="h-3 skeleton rounded w-20 mx-auto" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
