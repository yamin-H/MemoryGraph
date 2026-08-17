'use client';

import { useMetrics, useAnimatedCounter } from '@/lib/hooks';
import { SkeletonCard } from './Skeleton';
import { Database, BookOpen, Users, Zap } from 'lucide-react';

function StatCard({
  title,
  value,
  icon: Icon,
  suffix = '',
  colorScheme = 'amber',
  subtitle,
}: {
  title: string;
  value: number;
  icon: any;
  suffix?: string;
  colorScheme?: 'amber' | 'blue' | 'purple' | 'emerald';
  subtitle?: string;
}) {
  const animated = useAnimatedCounter(value);

  const colors = {
    amber: {
      iconBg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
      glow: 'hover:border-amber-500/40',
    },
    blue: {
      iconBg: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
      glow: 'hover:border-blue-500/40',
    },
    purple: {
      iconBg: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20',
      glow: 'hover:border-purple-500/40',
    },
    emerald: {
      iconBg: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
      glow: 'hover:border-emerald-500/40',
    },
  }[colorScheme];

  return (
    <div className={`glass-panel p-5 group ${colors.glow} transition-all duration-300 rounded-3xl border border-slate-200 dark:border-white/[0.08] shadow-md hover:-translate-y-1`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-mono">{title}</span>
        <div className={`w-10 h-10 rounded-2xl flex items-center justify-center border ${colors.iconBg} transition-transform group-hover:scale-110 shadow-sm`}>
          <Icon size={18} />
        </div>
      </div>
      <div className="flex items-baseline gap-1.5">
        <p className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-slate-100 font-mono tracking-tight">
          {animated.toLocaleString()}{suffix}
        </p>
      </div>
      {subtitle && (
        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 font-medium">{subtitle}</p>
      )}
    </div>
  );
}

export function MetricsDashboard() {
  const { metrics, loading } = useMetrics();

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        title="Facts Stored"
        value={metrics.total_facts_stored}
        icon={Database}
        colorScheme="amber"
        subtitle="HydraDB Fact nodes"
      />
      <StatCard
        title="Sessions Ingested"
        value={metrics.sessions_ingested}
        icon={BookOpen}
        colorScheme="purple"
        subtitle="Multi-turn dialogue sessions"
      />
      <StatCard
        title="Entities Tracked"
        value={metrics.entities_tracked}
        icon={Users}
        colorScheme="blue"
        subtitle="Persons, concepts & items"
      />
      <StatCard
        title="Avg Query Latency"
        value={Math.round(metrics.avg_query_latency_ms)}
        suffix="ms"
        icon={Zap}
        colorScheme="emerald"
        subtitle="Retrieval + Graph traversal"
      />
    </div>
  );
}
