'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { CompareResponse } from '@/lib/types';
import {
  Swords,
  CheckCircle2,
  Sparkles,
  Layers,
  Network,
  Code2,
  Search,
  RefreshCw,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Trophy,
} from 'lucide-react';
import { CodeViewer } from '@/components/CodeViewer';

export default function ArenaPage() {
  const [customQuestion, setCustomQuestion] = useState('');
  const [userId, setUserId] = useState('alex');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showDeepDive, setShowDeepDive] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  const runComparison = async (queryText: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const resp = await api.compareSystems(queryText, userId.trim() || 'user');
      setResult(resp);
    } catch (err: any) {
      setError(err?.message || 'Failed to execute side-by-side comparison');
    } finally {
      setLoading(false);
    }
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customQuestion.trim()) return;
    runComparison(customQuestion);
  };

  return (
    <>
      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes shimmer {
          0%   { background-position: -200% center; }
          100% { background-position:  200% center; }
        }
        @keyframes pulse-glow {
          0%, 100% { box-shadow: 0 0 20px -6px rgba(245,158,11,0.4); }
          50%       { box-shadow: 0 0 32px -4px rgba(245,158,11,0.7); }
        }
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        @keyframes battle-flicker {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.75; }
        }
        @keyframes progress-fill {
          from { width: 0%; }
          to   { width: 100%; }
        }
        @keyframes slide-in-left {
          from { opacity: 0; transform: translateX(-18px); }
          to   { opacity: 1; transform: translateX(0); }
        }
        @keyframes slide-in-right {
          from { opacity: 0; transform: translateX(18px); }
          to   { opacity: 1; transform: translateX(0); }
        }

        .fu { animation: fadeUp  0.5s cubic-bezier(.22,.68,0,1.1) both; }
        .fi { animation: fadeIn  0.4s ease both; }
        .sil { animation: slide-in-left  0.5s cubic-bezier(.22,.68,0,1.1) both; }
        .sir { animation: slide-in-right 0.5s cubic-bezier(.22,.68,0,1.1) both; }

        .d1 { animation-delay: 0.06s; }
        .d2 { animation-delay: 0.12s; }
        .d3 { animation-delay: 0.18s; }
        .d4 { animation-delay: 0.24s; }
        .d5 { animation-delay: 0.30s; }
        .d6 { animation-delay: 0.38s; }

        .shimmer-text {
          background: linear-gradient(105deg, #f59e0b 0%, #fbbf24 40%, #fde68a 55%, #f59e0b 100%);
          background-size: 200% auto;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          animation: shimmer 3.5s linear infinite;
        }

        .winner-pulse { animation: pulse-glow 2.4s ease-in-out infinite; }

        .loading-bar {
          animation: progress-fill 1.8s ease-in-out infinite alternate;
        }

        .vs-badge {
          animation: battle-flicker 2s ease-in-out infinite;
        }

        .arena-card {
          position: relative;
          background: #080d18;
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 20px;
          overflow: hidden;
          transition: border-color 0.3s, box-shadow 0.3s, transform 0.3s;
        }
        .arena-card::before {
          content: '';
          position: absolute;
          top: 0; left: 0; right: 0;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
        }
        .arena-card:hover {
          transform: translateY(-2px);
        }

        .rag-card::before {
          background: linear-gradient(90deg, transparent, rgba(244,63,94,0.3), transparent);
        }
        .rag-card { border-color: rgba(244,63,94,0.15); }
        .rag-card:hover { border-color: rgba(244,63,94,0.35); box-shadow: 0 0 40px -12px rgba(244,63,94,0.25); }

        .mem-card::before {
          background: linear-gradient(90deg, transparent, rgba(16,185,129,0.35), transparent);
        }
        .mem-card { border-color: rgba(16,185,129,0.18); }
        .mem-card:hover { border-color: rgba(16,185,129,0.40); box-shadow: 0 0 40px -12px rgba(16,185,129,0.25); }

        .scenario-btn {
          position: relative;
          overflow: hidden;
          transition: all 0.25s;
        }
        .scenario-btn::after {
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(135deg, rgba(255,255,255,0.03), transparent);
          opacity: 0;
          transition: opacity 0.25s;
        }
        .scenario-btn:hover::after { opacity: 1; }

        .grain-layer::after {
          content: '';
          position: absolute;
          inset: 0;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E");
          opacity: 0.025;
          pointer-events: none;
          border-radius: inherit;
        }

        .chunk-outdated {
          position: relative;
          overflow: hidden;
        }
        .chunk-outdated::before {
          content: '';
          position: absolute;
          top: 0; left: 0; right: 0;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(244,63,94,0.5), transparent);
        }
      `}</style>

      <div className="w-full max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

        {/* ── Header ── */}
        <div className="text-center space-y-4 max-w-2xl mx-auto pt-2">
          <div className={`${mounted ? 'fu d1' : 'opacity-0'} inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-amber-500/25 bg-amber-500/[0.07]`}>
            <Swords size={13} className="text-amber-400" />
            <span className="text-amber-300 text-[11px] font-black font-mono tracking-widest uppercase">
              Live Battle Arena · Track 03
            </span>
          </div>

          <h1 className={`${mounted ? 'fu d2' : 'opacity-0'} text-3xl sm:text-5xl font-black tracking-tight font-heading`}>
            <span className="text-white">Vector RAG</span>{' '}
            <span className="vs-badge inline-block text-slate-600 text-2xl sm:text-3xl font-black mx-1">vs</span>{' '}
            <span className="shimmer-text">MemoryGraph</span>
          </h1>

          <p className={`${mounted ? 'fu d3' : 'opacity-0'} text-xs sm:text-sm text-slate-500 leading-relaxed max-w-lg mx-auto`}>
            Watch vector similarity retrieve outdated memories, while HydraDB resolves{' '}
            <code className="text-amber-300 font-mono font-bold bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
              SUPERSEDES
            </code>{' '}
            edges and guarantees ground truth.
          </p>
        </div>

        {/* ── Query Input ── */}
        <form
          onSubmit={handleCustomSubmit}
          className={`${mounted ? 'fu d5' : 'opacity-0'} flex gap-2.5 max-w-2xl mx-auto`}
        >
          <div className="relative flex-1">
            <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600" />
            <input
              type="text"
              value={customQuestion}
              onChange={(e) => setCustomQuestion(e.target.value)}
              placeholder="Type any memory query to battle test…"
              className="w-full pl-11 pr-4 py-3 rounded-2xl bg-white/[0.03] border border-white/[0.08] text-white text-xs sm:text-sm placeholder:text-slate-600 focus:outline-none focus:border-amber-500/40 focus:bg-white/[0.05] focus:shadow-[0_0_20px_-6px_rgba(245,158,11,0.3)] transition-all duration-300 font-mono"
            />
          </div>
          <input
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            aria-label="User ID"
            placeholder="User ID"
            className="w-28 px-3 py-3 rounded-2xl bg-white/[0.03] border border-white/[0.08] text-white text-xs font-mono"
          />
          <button
            type="submit"
            disabled={loading || !customQuestion.trim()}
            className="flex items-center gap-2 px-6 py-3 rounded-2xl text-xs sm:text-sm font-bold text-slate-950 flex-shrink-0 transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              background: 'linear-gradient(135deg, #f59e0b, #fbbf24)',
              boxShadow: loading ? 'none' : '0 0 24px -4px rgba(245,158,11,0.5)',
            }}
          >
            {loading
              ? <RefreshCw size={14} style={{ animation: 'spin-slow 0.8s linear infinite' }} />
              : <Swords size={14} />
            }
            <span>{loading ? 'Running…' : 'Battle'}</span>
          </button>
        </form>

        {/* ── Loading State ── */}
        {loading && (
          <div className="fi max-w-2xl mx-auto space-y-3">
            <div className="relative h-1 rounded-full bg-white/[0.05] overflow-hidden">
              <div
                className="absolute left-0 top-0 h-full rounded-full loading-bar"
                style={{ background: 'linear-gradient(90deg, #f59e0b, #fbbf24, #10b981)' }}
              />
            </div>
            <div className="flex items-center justify-center gap-2 text-[11px] font-mono text-slate-600">
              <RefreshCw size={11} style={{ animation: 'spin-slow 1s linear infinite' }} />
              <span>Executing parallel retrieval…</span>
            </div>
          </div>
        )}

        {/* ── Error ── */}
        {error && (
          <div className="fi arena-card grain-layer max-w-2xl mx-auto p-4 border-rose-500/20 flex items-center gap-3">
            <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20">
              <AlertTriangle size={15} className="text-rose-400" />
            </div>
            <span className="text-rose-300 text-xs font-semibold">{error}</span>
          </div>
        )}

        {/* ── Results ── */}
        {result && !loading && (
          <div className="space-y-5 fi">

            {/* Winner Banner */}
            <div
              className="relative grain-layer rounded-3xl border border-amber-500/25 bg-[#0a0e1a] overflow-hidden p-5 sm:p-6 winner-pulse"
            >
              {/* bg glow */}
              <div className="absolute inset-0 bg-gradient-to-br from-amber-500/[0.06] via-transparent to-emerald-500/[0.04] pointer-events-none" />
              <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-400/50 to-transparent" />

              <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span
                      className="text-[11px] font-black uppercase px-3 py-1.5 rounded-xl text-slate-950 tracking-wider flex items-center gap-1.5"
                      style={{ background: 'linear-gradient(135deg, #f59e0b, #fbbf24)', boxShadow: '0 0 16px -4px rgba(245,158,11,0.6)' }}
                    >
                      <Trophy size={12} />
                      WINNER: {result.winner.toUpperCase()}
                    </span>
                    <span className="text-sm font-extrabold text-white font-heading">
                      {result.winner === 'memorygraph' ? 'Temporal Reality Resolved ✓' : 'Equal Accuracy'}
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-xl">
                    {result.diff_explanation}
                  </p>
                </div>

                <div className="flex-shrink-0 space-y-2">
                  <div
                    className="text-xs font-mono text-emerald-300 font-bold px-3 py-1.5 rounded-xl border border-emerald-500/25 bg-emerald-500/[0.08] text-right"
                    style={{ boxShadow: '0 0 14px -5px rgba(16,185,129,0.35)' }}
                  >
                    HydraDB: {result.memorygraph.latency_ms}ms
                  </div>
                  <div className="text-[11px] font-mono text-slate-600 text-right px-1">
                    Vector RAG: {result.vector_rag.latency_ms}ms
                  </div>
                </div>
              </div>
            </div>

            {/* Side-by-side cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

              {/* Vector RAG */}
              <div className="sil arena-card rag-card grain-layer p-5 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-white/[0.05]">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20">
                      <Layers size={14} className="text-rose-400" />
                    </div>
                    <span className="text-rose-300 text-xs sm:text-sm font-bold">Standard Vector RAG</span>
                  </div>
                  <span className="text-[9px] font-mono uppercase font-black px-2 py-1 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20 tracking-wider">
                    {result.vector_rag.failure_mode === 'retrieved_conflicting_temporal_facts'
                      ? '⚠ Conflict Risk'
                      : 'Top-K Retrieval'}
                  </span>
                </div>

                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-slate-600 font-mono tracking-wider">Retrieved Answer</span>
                  <div className="relative p-4 rounded-2xl bg-rose-500/[0.05] border border-rose-500/15 text-xs sm:text-sm text-rose-200 leading-relaxed min-h-[76px] overflow-hidden">
                    <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-rose-500/30 to-transparent" />
                    {result.vector_rag.answer}
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-600 font-mono pt-1">
                  <span>
                    Confidence:{' '}
                    <strong className="text-slate-300">{Math.round(result.vector_rag.confidence * 100)}%</strong>
                  </span>
                  <span>{result.vector_rag.retrieved_chunks.length} chunks analyzed</span>
                </div>

                {/* Confidence bar */}
                <div className="h-1 rounded-full bg-white/[0.05] overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-rose-600 to-rose-400 transition-all duration-700"
                    style={{ width: `${Math.round(result.vector_rag.confidence * 100)}%` }}
                  />
                </div>
              </div>

              {/* MemoryGraph */}
              <div className="sir arena-card mem-card grain-layer p-5 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-white/[0.05]">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20" style={{ boxShadow: '0 0 12px -4px rgba(16,185,129,0.3)' }}>
                      <Network size={14} className="text-emerald-400" />
                    </div>
                    <span className="text-emerald-300 text-xs sm:text-sm font-bold">MemoryGraph (HydraDB)</span>
                  </div>
                  <span className="text-[9px] font-mono uppercase font-black px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 tracking-wider">
                    ✓ Verified Truth
                  </span>
                </div>

                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-slate-600 font-mono tracking-wider">Verified Answer</span>
                  <div className="relative p-4 rounded-2xl bg-emerald-500/[0.06] border border-emerald-500/20 text-xs sm:text-sm text-emerald-100 font-semibold leading-relaxed min-h-[76px] overflow-hidden">
                    <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-400/40 to-transparent" />
                    {result.memorygraph.answer}
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-600 font-mono pt-1">
                  <span>
                    Confidence:{' '}
                    <strong className="text-emerald-400" style={{ textShadow: '0 0 10px rgba(16,185,129,0.5)' }}>
                      {Math.round(result.memorygraph.confidence * 100)}%
                    </strong>
                  </span>
                  <span className="text-emerald-600">{result.memorygraph.facts_examined} facts verified</span>
                </div>

                {/* Confidence bar */}
                <div className="h-1 rounded-full bg-white/[0.05] overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${Math.round(result.memorygraph.confidence * 100)}%`,
                      background: 'linear-gradient(90deg, #059669, #10b981)',
                      boxShadow: '0 0 8px rgba(16,185,129,0.5)',
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Deep Dive Accordion */}
            <div className="pt-1">
              <button
                onClick={() => setShowDeepDive(!showDeepDive)}
                className="w-full py-3.5 px-5 rounded-2xl bg-white/[0.02] border border-white/[0.07] hover:bg-white/[0.05] hover:border-white/[0.12] text-xs font-bold text-slate-400 hover:text-slate-200 flex items-center justify-between transition-all duration-300 cursor-pointer group"
              >
                <span className="flex items-center gap-2.5">
                  <Sparkles size={14} className="text-amber-500" />
                  <span>Deep-Dive: Retrieved Chunks vs. Active Subgraph</span>
                </span>
                <div className="p-1 rounded-lg bg-white/[0.04] group-hover:bg-white/[0.08] transition-colors">
                  {showDeepDive
                    ? <ChevronUp size={13} />
                    : <ChevronDown size={13} />}
                </div>
              </button>

              {showDeepDive && (
                <div className="mt-3 fu arena-card grain-layer p-5 sm:p-6 space-y-6">
                  <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.07] to-transparent" />

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    {/* Vector chunks */}
                    <div className="space-y-3">
                      <div className="flex items-center gap-2 text-[11px] font-mono font-bold uppercase tracking-widest text-slate-600">
                        <Layers size={11} className="text-rose-500" />
                        <span>Retrieved Vector Chunks</span>
                        <div className="flex-1 h-px bg-white/[0.05]" />
                      </div>
                      <div className="space-y-2">
                        {result.vector_rag.retrieved_chunks.map((chunk, i) => (
                          <div
                            key={i}
                            className={`chunk-outdated p-3.5 rounded-2xl border text-xs leading-relaxed overflow-hidden ${
                              chunk.is_outdated
                                ? 'bg-rose-500/[0.07] border-rose-500/20 text-rose-300'
                                : 'bg-white/[0.02] border-white/[0.06] text-slate-400'
                            }`}
                          >
                            <div className="flex items-center justify-between text-[10px] mb-2 font-mono">
                              <span className="text-slate-600">{chunk.session_id}</span>
                              {chunk.is_outdated && (
                                <span className="font-black text-rose-400 uppercase text-[9px] px-1.5 py-0.5 rounded bg-rose-500/15 border border-rose-500/20 tracking-wider">
                                  Superseded
                                </span>
                              )}
                            </div>
                            <p>{chunk.content}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Active facts */}
                    <div className="space-y-3">
                      <div className="flex items-center gap-2 text-[11px] font-mono font-bold uppercase tracking-widest text-slate-600">
                        <Network size={11} className="text-emerald-500" />
                        <span>Active HydraDB Facts</span>
                        <div className="flex-1 h-px bg-white/[0.05]" />
                      </div>
                      <div className="space-y-2">
                        {result.memorygraph.active_facts.map((fact, i) => (
                          <div
                            key={i}
                            className="relative p-3.5 rounded-2xl bg-emerald-500/[0.07] border border-emerald-500/20 text-xs text-emerald-200 leading-relaxed overflow-hidden"
                          >
                            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-400/35 to-transparent" />
                            <div className="flex items-center gap-1.5 text-[10px] text-emerald-500 font-bold mb-2 font-mono">
                              <CheckCircle2 size={11} />
                              <span>CURRENT · is_current: true</span>
                            </div>
                            <p>{fact}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* OpenCypher Query */}
                  <div className="space-y-3 pt-3 border-t border-white/[0.05]">
                    <div className="flex items-center gap-2 text-[11px] font-mono font-bold uppercase tracking-widest text-slate-600">
                      <Code2 size={11} className="text-amber-500" />
                      <span>OpenCypher Query Traversal</span>
                      <div className="flex-1 h-px bg-white/[0.05]" />
                    </div>
                    <div className="rounded-2xl overflow-hidden border border-white/[0.07]" style={{ boxShadow: '0 0 40px -15px rgba(0,0,0,0.8)' }}>
                      <CodeViewer
                        code={result.memorygraph.opencypher_query}
                        language="opencypher"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
