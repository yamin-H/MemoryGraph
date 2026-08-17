'use client';

import { useHealth } from '@/lib/hooks';
import { SkeletonBlock } from './Skeleton';
import { Server, Database, Radio, Cpu, RefreshCw, CheckCircle2, AlertTriangle } from 'lucide-react';

const serviceConfig = [
  { key: 'api', label: 'FastAPI Backend', icon: Server, desc: 'Port 8000 REST/SSE' },
  { key: 'hydradb', label: 'HydraDB Graph', icon: Database, desc: 'HydraDB Bolt :7687' },
  { key: 'redis', label: 'Redis Cache', icon: Radio, desc: 'Metrics & Rate Limiting' },
  { key: 'groq', label: 'Groq LLaMA 3.1', icon: Cpu, desc: 'Fast LLM Inference' },
];

export function HealthStatus() {
  const { health, loading, refetch } = useHealth();

  if (loading) {
    return (
      <div className="glass-panel p-6 rounded-3xl border border-slate-200 dark:border-white/[0.08]">
        <div className="flex items-center justify-between mb-4">
          <SkeletonBlock className="h-4 w-36" />
          <SkeletonBlock className="h-4 w-24" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="p-4 rounded-2xl bg-slate-100 dark:bg-white/[0.02] border border-slate-200 dark:border-white/[0.05] space-y-2">
              <SkeletonBlock className="h-3 w-20" />
              <SkeletonBlock className="h-2.5 w-28" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const isAllOk = health.status === 'ok';

  return (
    <div className="glass-panel p-6 rounded-3xl border border-slate-200 dark:border-white/[0.08] shadow-lg">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 tracking-tight font-heading">System Health & Services</h3>
          <span
            className={`inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1 rounded-full border shadow-sm ${
              isAllOk
                ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
                : 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30'
            }`}
          >
            {isAllOk ? <CheckCircle2 size={13} className="text-emerald-500" /> : <AlertTriangle size={13} className="text-amber-500" />}
            {isAllOk ? 'All Systems Operational' : 'Degraded Services'}
          </span>
        </div>
        <button
          onClick={() => refetch()}
          className="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 transition-colors p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-white/5 flex items-center gap-1.5 cursor-pointer"
          title="Refresh Health"
        >
          <RefreshCw size={13} />
          <span className="hidden sm:inline text-xs font-semibold">Refresh</span>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {serviceConfig.map((svc) => {
          const serviceData = health?.services?.[svc.key as keyof typeof health.services];
          const isHealthy = serviceData?.status === 'ok';
          const Icon = svc.icon;

          return (
            <div
              key={svc.key}
              className="p-4 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-white/[0.06] hover:border-slate-300 dark:hover:border-white/[0.15] transition-all flex items-start gap-3.5 shadow-sm"
            >
              <div className={`p-2.5 rounded-xl border ${isHealthy ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'}`}>
                <Icon size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold text-slate-900 dark:text-slate-200 truncate">{svc.label}</p>
                  <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50' : 'bg-rose-500'}`} />
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 truncate font-medium">{svc.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
