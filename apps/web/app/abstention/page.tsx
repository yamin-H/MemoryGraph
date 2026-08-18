'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { AbstentionInspectionResponse } from '@/lib/types';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Search,
  RefreshCw,
  Code2,
  Layers,
  Flame,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { CodeViewer } from '@/components/CodeViewer';

export default function AbstentionPage() {
  const [question, setQuestion] = useState('');
  const [userId, setUserId] = useState('user');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AbstentionInspectionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showTechnicalTrace, setShowTechnicalTrace] = useState(false);

  const runInspection = async (queryText: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.inspectAbstention(queryText, userId.trim() || 'user');
      setData(resp);
    } catch (err: any) {
      console.error('Abstention error:', err);
      setError(err?.message || 'Failed to verify query against graph');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    runInspection(question);
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center space-y-3 max-w-2xl mx-auto pt-2">
        <div className="animate-fade-in-up stagger-1 inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/25 text-blue-700 dark:text-blue-400 text-xs font-bold font-mono shadow-sm">
          <ShieldCheck size={14} className="text-blue-500" />
          <span>Hallucination Guard · Track 03 Core</span>
        </div>
        <h1 className="animate-fade-in-up stagger-2 text-2xl sm:text-4xl font-black text-slate-900 dark:text-white tracking-tight font-heading">
          Honest Abstention & Truth Guarantee
        </h1>
        <p className="animate-fade-in-up stagger-3 text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed max-w-lg mx-auto font-medium">
          Standard LLMs hallucinate when facts don&apos;t exist. MemoryGraph checks HydraDB entity boundaries and honestly says{' '}
          <span className="text-amber-600 dark:text-amber-300 font-bold">&ldquo;I don&apos;t know&rdquo;</span>.
        </p>
      </div>

      {/* Query Bar */}
      <form onSubmit={handleSubmit} className="flex gap-2.5 max-w-2xl mx-auto animate-fade-in-up stagger-5">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Type any question to test honest abstention..."
            className="input-field pl-11 pr-4 py-3 text-xs sm:text-sm shadow-sm"
          />
        </div>
        <input
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          aria-label="User ID"
          placeholder="User ID"
          className="input-field w-28 py-3 text-xs font-mono"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="btn-primary text-xs sm:text-sm px-6 py-3 flex-shrink-0 shadow-md"
        >
          {loading ? <RefreshCw size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
          <span>Verify</span>
        </button>
      </form>

      {/* Error */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/25 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2.5 max-w-2xl mx-auto animate-fade-in">
          <AlertTriangle size={16} className="flex-shrink-0" />
          <span className="font-semibold">{error}</span>
        </div>
      )}

      {/* Results */}
      {data && (
        <div className="space-y-5 animate-fade-in-up">
          {/* Verdict Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-2">
            <div className="flex items-center gap-3">
              <span
                className={`text-xs font-bold px-3.5 py-1.5 rounded-xl flex items-center gap-2 border shadow-sm ${
                  data.abstention_triggered
                    ? 'bg-rose-500/15 text-rose-800 dark:text-rose-300 border-rose-500/30'
                    : 'bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border-emerald-500/30'
                }`}
              >
                {data.abstention_triggered ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />}
                {data.abstention_triggered ? 'Honest Abstention Enforced' : 'Verified Knowledge Grounded'}
              </span>
              <span className="text-xs text-slate-600 dark:text-slate-400 font-medium">
                Calibrated Confidence:{' '}
                <strong className="text-slate-900 dark:text-white font-mono text-sm">
                  {Math.round((data.confidence_breakdown?.final_confidence || 0) * 100)}%
                </strong>
              </span>
            </div>
            <span className="text-xs font-mono text-slate-500 font-bold">{data.latency_ms} ms</span>
          </div>

          {/* Side-by-Side Comparison */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Standard AI */}
            <div className="feature-card space-y-4 !border-rose-500/20 shadow-md">
              <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-white/[0.06]">
                <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400 text-xs sm:text-sm font-bold">
                  <Flame size={16} />
                  <span>Standard AI (Vector RAG)</span>
                </div>
                <span className="text-[10px] font-mono uppercase font-bold px-2.5 py-0.5 rounded-lg bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20">
                  Hallucination Risk
                </span>
              </div>
              <div className="p-4 rounded-2xl bg-rose-500/[0.04] dark:bg-black/30 border border-rose-500/20 text-xs sm:text-sm text-rose-900 dark:text-rose-200 italic leading-relaxed min-h-[64px] font-medium">
                &ldquo;{data.hallucination_simulation}&rdquo;
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed font-medium">
                Without graph boundaries, naive models guess plausible answers instead of acknowledging unrecorded information.
              </p>
            </div>

            {/* MemoryGraph */}
            <div className="feature-card space-y-4 !border-emerald-500/30 shadow-md">
              <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-white/[0.06]">
                <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 text-xs sm:text-sm font-bold">
                  <ShieldCheck size={16} />
                  <span>MemoryGraph (HydraDB)</span>
                </div>
                <span className="text-[10px] font-mono uppercase font-bold px-2.5 py-0.5 rounded-lg bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/25">
                  Honest & Calibrated
                </span>
              </div>
              <div className="p-4 rounded-2xl bg-emerald-500/[0.06] dark:bg-black/30 border border-emerald-500/25 text-xs sm:text-sm text-emerald-950 dark:text-emerald-100 font-semibold leading-relaxed min-h-[64px]">
                {data.verified_answer}
              </div>
              {data.related_facts_in_graph && data.related_facts_in_graph.length > 0 && (
                <div className="text-xs text-slate-600 dark:text-slate-400 pt-1 font-medium">
                  <span className="text-slate-500 font-bold">Recorded fact: </span>
                  <span className="text-slate-800 dark:text-slate-300">{data.related_facts_in_graph[0]}</span>
                </div>
              )}
            </div>
          </div>

          {/* Technical Trace Accordion */}
          <div className="pt-2">
            <button
              onClick={() => setShowTechnicalTrace(!showTechnicalTrace)}
              className="w-full py-3 px-5 rounded-2xl glass-card border border-slate-200 dark:border-white/[0.08] text-xs font-bold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white flex items-center justify-between transition-all duration-300 shadow-sm"
            >
              <span className="flex items-center gap-2">
                <Layers size={15} className="text-blue-500" />
                <span>Deep-Dive: 4-Stage Graph Reasoning Trace</span>
              </span>
              {showTechnicalTrace ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </button>

            {showTechnicalTrace && (
              <div className="mt-4 p-5 rounded-3xl glass-panel border border-slate-200 dark:border-white/[0.08] space-y-5 animate-fade-in-up shadow-xl">
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3.5">
                  {/* Step 1: Entity Index */}
                  <div className="p-4 rounded-2xl bg-white dark:bg-black/40 border border-slate-200 dark:border-white/[0.06] space-y-2.5 shadow-sm">
                    <span className="section-label">1. Entity Index</span>
                    <div className="space-y-1.5 pt-1">
                      {data.extracted_entities.map((e, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <span className="text-slate-700 dark:text-slate-300 font-medium">{e.entity}</span>
                          <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${e.in_graph ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400' : 'bg-rose-500/15 text-rose-700 dark:text-rose-400'}`}>
                            {e.in_graph ? 'FOUND' : 'MISSING'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Step 2: Subgraph Evidence */}
                  <div className="p-4 rounded-2xl bg-white dark:bg-black/40 border border-slate-200 dark:border-white/[0.06] space-y-2.5 shadow-sm">
                    <span className="section-label">2. Graph Evidence (Cypher)</span>
                    <div className="text-xs text-slate-600 dark:text-slate-300 pt-1 space-y-2 font-medium">
                      <div className="flex justify-between">
                        <span>Retrieved Nodes:</span>
                        <span className="font-mono font-bold text-amber-600 dark:text-amber-400">{data.subgraph_nodes_found}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Entity Support:</span>
                        <span className="font-mono font-bold text-sky-600 dark:text-sky-400">
                          {data.graph_evidence && Object.keys(data.graph_evidence).length > 0
                            ? `${Object.values(data.graph_evidence).reduce((acc, v) => acc + v.supporting_facts, 0)} facts`
                            : '0 facts'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Step 3: Graph Density & Coverage */}
                  <div className="p-4 rounded-2xl bg-white dark:bg-black/40 border border-slate-200 dark:border-white/[0.06] space-y-2.5 shadow-sm">
                    <span className="section-label">3. Topology Coverage</span>
                    <div className="text-xs text-slate-600 dark:text-slate-300 pt-1 space-y-2 font-medium">
                      <div className="flex justify-between">
                        <span>Relation Density:</span>
                        <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">{Math.round((data.confidence_breakdown?.relation_density || 0) * 100)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Entity Coverage:</span>
                        <span className="font-mono font-bold text-purple-600 dark:text-purple-400">{Math.round((data.confidence_breakdown?.entity_coverage || 0) * 100)}%</span>
                      </div>
                    </div>
                  </div>

                  {/* Step 4: Calibrated Decision */}
                  <div className="p-4 rounded-2xl bg-white dark:bg-black/40 border border-slate-200 dark:border-white/[0.06] space-y-2.5 shadow-sm">
                    <span className="section-label">4. Calibrated Decision</span>
                    <div className="text-xs text-slate-600 dark:text-slate-300 pt-1 space-y-2 font-medium">
                      <div className="flex justify-between">
                        <span>Score:</span>
                        <span className="font-mono font-bold text-slate-900 dark:text-white">{Math.round((data.confidence_breakdown?.final_confidence || 0) * 100)}%</span>
                      </div>
                      <div className="flex justify-between text-slate-500">
                        <span>Threshold (τ):</span>
                        <span className="font-mono font-bold">35%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Mathematical Formula Callout */}
                <div className="p-3.5 rounded-2xl bg-amber-500/5 border border-amber-500/20 text-xs font-mono text-slate-700 dark:text-slate-300">
                  <span className="text-[10px] uppercase font-bold text-amber-600 dark:text-amber-400 block mb-1">
                    Graph-Native Calibration Formula (confidence.py)
                  </span>
                  <code>final_score = 0.35 * coverage + 0.45 * density + 0.20 * relationship_coverage - conflict_penalty</code>
                </div>

                {/* OpenCypher Query */}
                <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-white/[0.06]">
                  <span className="section-label">
                    <Code2 size={13} className="text-amber-500" />
                    HydraDB OpenCypher Query
                  </span>
                  <div className="rounded-2xl overflow-hidden border border-slate-800 shadow-md">
                    <CodeViewer
                      code={data.opencypher_inspection}
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
  );
}
