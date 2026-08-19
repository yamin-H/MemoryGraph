'use client';

import { use, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function EntityGraphRedirectPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const resolvedParams = use(params);
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const entityName = resolvedParams.name;
    const userId = searchParams.get('user_id') || 'alex';
    router.replace(`/graph?entity=${encodeURIComponent(entityName)}&user_id=${encodeURIComponent(userId)}`);
  }, [resolvedParams, searchParams, router]);

  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
      <div className="w-10 h-10 border-2 border-amber-500/40 border-t-amber-500 rounded-full animate-spin" />
      <span className="text-xs font-semibold font-mono text-slate-600 dark:text-slate-400">
        Navigating to Graph for {resolvedParams.name}...
      </span>
    </div>
  );
}
