'use client';

import { BenchmarkTable } from '@/components/BenchmarkTable';
import { BarChart3, ShieldCheck, Zap, Layers } from 'lucide-react';

export default function BenchmarkPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center space-y-3 max-w-2xl mx-auto pt-2">
        <div className="animate-fade-in-up stagger-1 inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/25 text-indigo-700 dark:text-indigo-400 text-xs font-bold font-mono shadow-sm">
          <BarChart3 size={14} className="text-indigo-500" />
          <span>Empirical Architecture Benchmark</span>
        </div>
        <h1 className="animate-fade-in-up stagger-2 text-2xl sm:text-4xl font-black text-slate-900 dark:text-white tracking-tight font-heading">
          Accuracy & Abstention Evaluation
        </h1>
        <p className="animate-fade-in-up stagger-3 text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed max-w-lg mx-auto font-medium">
          Comparing Graph-Native Memory on HydraDB against vector RAG, long-context prompting, and mem0 key-value memory.
        </p>
      </div>

      {/* Feature Highlight Cards */}
      <div className="animate-fade-in-up stagger-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="feature-card space-y-2.5 !border-emerald-500/25 shadow-md">
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-bold text-xs sm:text-sm">
            <Zap size={16} />
            <span>Temporal Fact Updates</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
            Up to +19% gain on superseded facts using recursive <code className="text-amber-700 dark:text-amber-300 font-mono font-bold bg-amber-500/10 px-1 rounded">SUPERSEDES</code> edges in HydraDB.
          </p>
        </div>

        <div className="feature-card space-y-2.5 !border-blue-500/25 shadow-md">
          <div className="flex items-center gap-2 text-blue-700 dark:text-blue-400 font-bold text-xs sm:text-sm">
            <Layers size={16} />
            <span>Multi-Session Synthesis</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
            Links entities and facts across non-contiguous dialogues spanning multiple days with zero context loss.
          </p>
        </div>

        <div className="feature-card space-y-2.5 !border-amber-500/25 shadow-md">
          <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-bold text-xs sm:text-sm">
            <ShieldCheck size={16} />
            <span>Calibrated Abstention</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
            Abstains gracefully with zero hallucinations when information was never discussed.
          </p>
        </div>
      </div>

      {/* Evaluation Table */}
      <section className="space-y-4 animate-fade-in-up stagger-5">
        <div className="section-label">
          <BarChart3 size={13} className="text-amber-500" />
          <span>Evaluation Datasets & Accuracy Scores</span>
        </div>
        <BenchmarkTable />
      </section>
    </div>
  );
}
