'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { SessionItem } from '@/lib/types';
import { MetricsDashboard } from '@/components/MetricsDashboard';
import { HealthStatus } from '@/components/HealthStatus';
import { SessionTimeline } from '@/components/SessionTimeline';
import { MessageSquare, Network, BarChart3, Upload, ArrowRight, Sparkles, Clock, Database } from 'lucide-react';
import { SkeletonBlock } from '@/components/Skeleton';

const featureActions = [
  {
    href: '/chat',
    icon: MessageSquare,
    title: 'Agent Memory Chat',
    description: 'Ask multi-session questions and query temporal fact chains with confidence scoring.',
    badge: 'Retrieval Layer',
    color: 'from-amber-500/10 to-amber-600/5',
    accent: 'text-amber-400',
  },
  {
    href: '/graph',
    icon: Network,
    title: '3D Graph Explorer',
    description: 'Interactive visualization of Session, Fact, Entity & Supersedence relationships.',
    badge: 'HydraDB Visualizer',
    color: 'from-blue-500/10 to-blue-600/5',
    accent: 'text-blue-400',
  },
  {
    href: '/ingest',
    icon: Upload,
    title: 'Ingest Conversation',
    description: 'Parse multi-turn dialogue into entities, temporal facts, and graph anchors in HydraDB.',
    badge: 'Pipeline',
    color: 'from-emerald-500/10 to-emerald-600/5',
    accent: 'text-emerald-400',
  },
  {
    href: '/benchmark',
    icon: BarChart3,
    title: 'Evaluation Matrix',
    description: 'Review LongMemEval and BEAM benchmarks comparing MemoryGraph against vector RAG & mem0.',
    badge: 'Benchmarks',
    color: 'from-purple-500/10 to-purple-600/5',
    accent: 'text-purple-400',
  },
];

export default function HomePage() {
  const [recentSessions, setRecentSessions] = useState<SessionItem[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);

  useEffect(() => {
    async function loadSessions() {
      try {
        const list = await api.getRecentSessions(5);
        setRecentSessions(list);
      } catch (err) {
        console.warn('Could not load recent sessions:', err);
      } finally {
        setLoadingSessions(false);
      }
    }
    loadSessions();
  }, []);

  return (
    <div className="max-w-7xl mx-auto p-6 sm:p-8 space-y-8 animate-[fadeIn_0.3s_ease-out]">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden glass-card p-6 sm:p-8 border border-white/[0.08] bg-gradient-to-r from-amber-500/[0.08] via-slate-900/60 to-slate-900/80">
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/25 text-amber-400 text-xs font-semibold">
            <Sparkles size={13} />
            <span>HydraDB Graph-Native Memory Layer</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
            Graph-Native Temporal Agent Memory
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-2xl">
            MemoryGraph stores conversation memories as interconnected facts and entities in HydraDB, tracking how facts evolve over time with automatic supersedence and confidence-aware abstention.
          </p>
          <div className="pt-2 flex flex-wrap gap-3">
            <Link href="/chat" className="btn-primary text-xs">
              <MessageSquare size={15} />
              <span>Start Agent Chat</span>
            </Link>
            <Link href="/graph" className="btn-secondary text-xs">
              <Network size={15} />
              <span>Explore Graph Nodes</span>
            </Link>
          </div>
        </div>

        {/* Decorative background glow */}
        <div className="absolute right-0 top-0 bottom-0 w-96 bg-gradient-to-l from-amber-500/10 to-transparent pointer-events-none" />
      </div>

      {/* Metrics Section */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono">
            LIVE KNOWLEDGE GRAPH METRICS
          </h2>
          <span className="text-xs text-slate-500 font-mono">Auto-refreshed via Redis</span>
        </div>
        <MetricsDashboard />
      </section>

      {/* Service Health Section */}
      <section className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono">
          STORAGE & INFERENCE STATUS
        </h2>
        <HealthStatus />
      </section>

      {/* Split section: Core Modules & Live Ingested Sessions */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Quick Launch Cards */}
        <section className="lg:col-span-8 space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono">
            CORE MODULES & CAPABILITIES
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {featureActions.map((action) => {
              const Icon = action.icon;
              return (
                <Link
                  key={action.href}
                  href={action.href}
                  className={`group glass-card glass-card-interactive p-5 flex flex-col justify-between bg-gradient-to-br ${action.color}`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-white/[0.06] text-slate-300">
                        {action.badge}
                      </span>
                      <div className={`p-2 rounded-xl bg-slate-900 border border-white/[0.08] ${action.accent} transition-transform group-hover:scale-110`}>
                        <Icon size={18} />
                      </div>
                    </div>
                    <h3 className="text-sm font-bold text-slate-100 group-hover:text-amber-300 transition-colors">
                      {action.title}
                    </h3>
                    <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                      {action.description}
                    </p>
                  </div>

                  <div className="pt-4 flex items-center justify-end text-xs font-semibold text-slate-400 group-hover:text-amber-400 transition-colors gap-1">
                    <span>Open</span>
                    <ArrowRight size={13} className="transition-transform group-hover:translate-x-1" />
                  </div>
                </Link>
              );
            })}
          </div>
        </section>

        {/* Live Recent Sessions Timeline */}
        <section className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
              <Clock size={13} className="text-amber-400" />
              RECENT SESSIONS
            </h2>
            <Link href="/graph" className="text-[11px] text-amber-400 hover:underline">
              View All
            </Link>
          </div>

          <div className="glass-card p-4">
            {loadingSessions ? (
              <div className="space-y-3 py-2">
                <SkeletonBlock className="h-16 w-full" />
                <SkeletonBlock className="h-16 w-full" />
              </div>
            ) : recentSessions.length > 0 ? (
              <SessionTimeline sessions={recentSessions} />
            ) : (
              <div className="text-center py-8 text-xs text-slate-500 space-y-2">
                <Database size={24} className="mx-auto text-slate-600 opacity-60" />
                <p>No active sessions in HydraDB yet.</p>
                <Link href="/ingest" className="inline-block text-amber-400 hover:underline text-[11px]">
                  Ingest demo conversation →
                </Link>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}