'use client';

import { BenchmarkTable } from '@/components/BenchmarkTable';
import { BarChart3, ShieldCheck, Zap, Layers } from 'lucide-react';

export default function BenchmarkPage() {
  return (
    <div className="max-w-7xl mx-auto p-6 sm:p-8 space-y-8 animate-[fadeIn_0.3s_ease-out]">
      {/* Header Info */}
      <div className="glass-card p-6 sm:p-8 border border-white/[0.08] bg-gradient-to-r from-purple-500/[0.08] via-slate-900/60 to-slate-900/80">
        <div className="max-w-3xl space-y-2.5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/25 text-purple-400 text-xs font-semibold">
            <BarChart3 size={13} />
            <span>Empirical Architecture Benchmark</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            MemoryGraph Accuracy & Abstention Evaluation
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            Comparing Graph-Native Memory on HydraDB against conventional vector RAG, Long-Context window prompting, and mem0 key-value memory across temporal fact updates, synthesis, and abstention scenarios.
          </p>
        </div>
      </div>

      {/* Feature Highlights Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass-card p-4 space-y-1.5 border border-emerald-500/20 bg-emerald-500/[0.02]">
          <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs">
            <Zap size={14} />
            <span>Temporal Fact Updates</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Up to +19% gain on superseded facts using explicit <code className="text-amber-300">SUPERSEDES</code> relationships in HydraDB.
          </p>
        </div>

        <div className="glass-card p-4 space-y-1.5 border border-blue-500/20 bg-blue-500/[0.02]">
          <div className="flex items-center gap-2 text-blue-400 font-bold text-xs">
            <Layers size={14} />
            <span>Multi-Session Synthesis</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Consistently links entities and facts across non-contiguous dialogues spanning multiple days.
          </p>
        </div>

        <div className="glass-card p-4 space-y-1.5 border border-amber-500/20 bg-amber-500/[0.02]">
          <div className="flex items-center gap-2 text-amber-400 font-bold text-xs">
            <ShieldCheck size={14} />
            <span>Confidence-Aware Abstention</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Abstains gracefully with zero hallucinations when requested information was never discussed.
          </p>
        </div>
      </div>

      {/* Evaluation Table */}
      <section className="space-y-4">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono">
          EVALUATION DATASETS & ACCURACY SCORES
        </h2>
        <BenchmarkTable />
      </section>
    </div>
  );
}
