export default function CompanyLoading() {
  return (
    <div className="space-y-6">
      {/* Company header skeleton */}
      <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="h-7 skeleton rounded w-56" />
            <div className="h-4 skeleton rounded w-32" />
            <div className="h-3 skeleton rounded w-24" />
          </div>
          <div className="text-right space-y-2">
            <div className="h-8 skeleton rounded w-32" />
            <div className="h-4 skeleton rounded w-24 ml-auto" />
          </div>
        </div>
        <div className="mt-4 flex gap-6">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="space-y-1">
              <div className="h-3 skeleton rounded w-16" />
              <div className="h-4 skeleton rounded w-20" />
            </div>
          ))}
        </div>
      </div>

      {/* Main grid skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* AI summary skeleton */}
        <div className="lg:col-span-2 rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 p-6 space-y-3">
          <div className="h-5 skeleton rounded w-40" />
          <div className="h-3 skeleton rounded w-full" />
          <div className="h-3 skeleton rounded w-5/6" />
          <div className="h-3 skeleton rounded w-4/5" />
          <div className="h-3 skeleton rounded w-full" />
          <div className="h-3 skeleton rounded w-3/4" />
        </div>

        {/* Quality score skeleton */}
        <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 p-6 space-y-4">
          <div className="h-5 skeleton rounded w-28" />
          <div className="flex items-center justify-center py-4">
            <div className="w-24 h-24 skeleton rounded-full" />
          </div>
          {[...Array(4)].map((_, i) => (
            <div key={i} className="space-y-1">
              <div className="flex justify-between">
                <div className="h-3 skeleton rounded w-20" />
                <div className="h-3 skeleton rounded w-8" />
              </div>
              <div className="h-1.5 skeleton rounded-full w-full" />
            </div>
          ))}
        </div>
      </div>

      {/* Tab nav skeleton */}
      <div className="flex gap-1 border-b border-gray-100 dark:border-gray-900 pb-0">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-9 skeleton rounded-t-lg w-24" />
        ))}
      </div>
    </div>
  );
}
