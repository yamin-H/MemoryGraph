'use client';

import { useMetrics, useAnimatedCounter } from '@/lib/hooks';
import { SkeletonCard } from './Skeleton';
import { Database, BookOpen, Users, Zap, MessageSquare, Flame } from 'lucide-react';

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
      iconBg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      glow: 'group-hover:border-amber-500/30',
    },
    blue: {
      iconBg: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      glow: 'group-hover:border-blue-500/30',
    },
    purple: {
      iconBg: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
      glow: 'group-hover:border-purple-500/30',
    },
    emerald: {
      iconBg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      glow: 'group-hover:border-emerald-500/30',
    },
  }[colorScheme];

  return (
    <div className={`glass-card p-5 group ${colors.glow} transition-all duration-300`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</span>
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${colors.iconBg} transition-transform group-hover:scale-110`}>
          <Icon size={17} />
        </div>
      </div>
      <div className="flex items-baseline gap-1.5">
        <p className="text-2xl sm:text-3xl font-extrabold text-slate-100 font-mono tracking-tight">
          {animated.toLocaleString()}{suffix}
        </p>
      </div>
      {subtitle && (
        <p className="text-[11px] text-slate-500 mt-1.5">{subtitle}</p>
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
        subtitle="Multi-turn conversation sessions"
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
