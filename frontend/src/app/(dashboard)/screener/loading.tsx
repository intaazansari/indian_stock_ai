export default function ScreenerLoading() {
  return (
    <div className="flex gap-6">
      {/* Filter panel skeleton */}
      <aside className="w-64 shrink-0 space-y-5">
        <div className="h-4 skeleton rounded w-20" />
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-8 skeleton rounded-lg" />
          ))}
        </div>
        <div className="space-y-2">
          <div className="h-3 skeleton rounded w-24" />
          <div className="h-8 skeleton rounded-md" />
          <div className="h-8 skeleton rounded-md" />
        </div>
        <div className="space-y-2">
          <div className="h-3 skeleton rounded w-28" />
          <div className="h-8 skeleton rounded-md" />
          <div className="h-8 skeleton rounded-md" />
        </div>
        <div className="h-9 skeleton rounded-lg" />
      </aside>

      {/* Table skeleton */}
      <div className="flex-1 min-w-0 space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1.5">
            <div className="h-5 skeleton rounded w-32" />
            <div className="h-3 skeleton rounded w-48" />
          </div>
          <div className="h-8 skeleton rounded-md w-36" />
        </div>

        <div className="rounded-xl border border-gray-100 dark:border-gray-900 overflow-hidden bg-white dark:bg-gray-950">
          {/* Header row */}
          <div className="flex gap-4 px-4 py-3 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-100 dark:border-gray-900">
            {[200, 60, 80, 60, 60, 60, 70, 70, 70, 60, 55].map((w, i) => (
              <div key={i} className="skeleton rounded" style={{ height: 14, width: w, flexShrink: 0 }} />
            ))}
          </div>
          {/* Data rows */}
          {[...Array(10)].map((_, i) => (
            <div key={i} className="flex gap-4 px-4 py-3.5 border-b border-gray-50 dark:border-gray-900">
              <div className="space-y-1.5 flex-shrink-0" style={{ width: 200 }}>
                <div className="h-3.5 skeleton rounded w-36" />
                <div className="h-3 skeleton rounded w-24" />
              </div>
              {[60, 80, 60, 60, 60, 70, 70, 70, 60, 55].map((w, j) => (
                <div key={j} className="skeleton rounded ml-auto" style={{ height: 14, width: w, flexShrink: 0 }} />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
