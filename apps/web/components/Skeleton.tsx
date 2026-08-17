'use client';

export function SkeletonBlock({ className = '' }: { className?: string }) {
  return <div className={`skeleton-box ${className}`} />;
}

export function SkeletonCard() {
  return (
    <div className="glass-panel p-5 space-y-3.5 rounded-3xl border border-slate-200 dark:border-white/[0.08]">
      <div className="flex items-center justify-between">
        <SkeletonBlock className="h-3.5 w-24" />
        <SkeletonBlock className="h-9 w-9 rounded-xl" />
      </div>
      <SkeletonBlock className="h-8 w-24" />
      <SkeletonBlock className="h-3 w-32" />
    </div>
  );
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonBlock
          key={i}
          className={`h-3.5 ${i === lines - 1 ? 'w-3/4' : 'w-full'}`}
        />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 4, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="glass-panel overflow-hidden rounded-3xl border border-slate-200 dark:border-white/[0.08]">
      <div className="p-4 border-b border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.02]">
        <div className="flex gap-4">
          {Array.from({ length: cols }).map((_, i) => (
            <SkeletonBlock key={i} className="h-4 flex-1" />
          ))}
        </div>
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="p-4 border-b border-slate-200 dark:border-white/5 last:border-b-0">
          <div className="flex gap-4">
            {Array.from({ length: cols }).map((_, j) => (
              <SkeletonBlock key={j} className="h-4 flex-1" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
