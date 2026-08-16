'use client';

import { useHealth } from '@/lib/hooks';
import { SkeletonBlock } from './Skeleton';
import { Server, Database, Radio, Cpu, RefreshCw } from 'lucide-react';

const serviceConfig = [
  { key: 'api', label: 'FastAPI Backend', icon: Server, desc: 'Port 8000 REST/SSE' },
  { key: 'hydradb', label: 'HydraDB Graph', icon: Database, desc: 'Neo4j Bolt :7687' },
  { key: 'redis', label: 'Redis Cache', icon: Radio, desc: 'Metrics & Rate Limiting' },
  { key: 'groq', label: 'Groq LLaMA 3.1', icon: Cpu, desc: 'Fast LLM Inference' },
];

export function HealthStatus() {
  const { health, loading, refetch } = useHealth();

  if (loading) {
    return (
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <SkeletonBlock className="h-4 w-32" />
          <SkeletonBlock className="h-4 w-20" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.05] space-y-2">
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
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <h3 className="text-sm font-semibold text-slate-100 tracking-tight">System Health & Services</h3>
          <span
            className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-0.5 rounded-full border ${
              isAllOk
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isAllOk ? 'bg-emerald-400' : 'bg-amber-400'} animate-pulse`} />
            {isAllOk ? 'All Systems Operational' : 'Degraded Services'}
          </span>
        </div>
        <button
          onClick={() => refetch()}
          className="text-xs text-slate-400 hover:text-slate-200 transition-colors p-1.5 rounded-lg hover:bg-white/5 flex items-center gap-1.5"
          title="Refresh Health"
        >
          <RefreshCw size={13} />
          <span className="hidden sm:inline text-[11px]">Refresh</span>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {serviceConfig.map((svc) => {
          const serviceData = health?.services?.[svc.key as keyof typeof health.services];
          const isHealthy = serviceData?.status === 'ok';
          const Icon = svc.icon;

          return (
            <div
              key={svc.key}
              className="p-3.5 rounded-xl bg-slate-900/60 border border-white/[0.06] hover:border-white/[0.12] transition-colors flex items-start gap-3"
            >
              <div className={`p-2 rounded-lg ${isHealthy ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                <Icon size={16} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold text-slate-200 truncate">{svc.label}</p>
                  <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5 truncate">{svc.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
