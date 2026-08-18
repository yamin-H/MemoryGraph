'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { MultiEntityResponse } from '@/lib/types';
import {
  Workflow,
  Search,
  RefreshCw,
  AlertTriangle,
  Code2,
  Clock,
  Layers,
  Sparkles,
  GitFork,
  CheckCircle2,
  Cpu,
  ArrowRight,
} from 'lucide-react';
import { CodeViewer } from '@/components/CodeViewer';

export default function MultiEntityPage() {
  const [entitiesInput, setEntitiesInput] = useState('Alex, Dhaka');
  const [userId, setUserId] = useState('user');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<MultiEntityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null);

  const quickPresets = [
    { label: 'Alex + Dhaka', entities: 'Alex, Dhaka' },
    { label: 'Alex + Pixel', entities: 'Alex, Pixel' },
    { label: 'Alex + Tech Startup', entities: 'Alex, Tech Startup' },
    { label: 'Dhaka + Rajshahi', entities: 'Dhaka, Rajshahi' },
  ];

  const handleQuery = async (inputStr?: string) => {
    const rawEntities = inputStr !== undefined ? inputStr : entitiesInput;
    const entityList = rawEntities
      .split(',')
      .map((e) => e.trim())
      .filter(Boolean);

    if (entityList.length === 0) {
      setError('Please provide at least one entity name');
      return;
    }

    setLoading(true);
    setError(null);
    setSelectedPathId(null);

    try {
      const resp = await api.getMultiEntityPaths(userId.trim() || 'user', entityList);
      setData(resp);
      if (resp.paths && resp.paths.length > 0) {
        setSelectedPathId(resp.paths[0].path_id);
      }
    } catch (err: any) {
      console.error('Multi-entity retrieval failed:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to execute HydraDB algo.MSpaths query');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleQuery();
  };

  const cypherQuerySnippet = `// HydraDB SuiteSparse GraphBLAS Native Procedure
CALL algo.MSpaths({
  sourceLabel: 'Entity',
  sourceProperty: 'name',
  sourceValues: [${entitiesInput.split(',').map((s) => `'${s.trim()}'`).filter(Boolean).join(', ')}],
  targetValues: [${entitiesInput.split(',').map((s) => `'${s.trim()}'`).filter(Boolean).join(', ')}],
  pairwise: true,
  relTypes: ['SUPERSEDES', 'MENTIONS', 'ASSERTS'],
  relDirection: 'both',
  maxLen: 5,
  pathCount: 10,
  resultLimit: 100
})
YIELD path
RETURN path`;

  return (
    <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center space-y-3 max-w-2xl mx-auto pt-2">
        <div className="animate-fade-in-up stagger-1 inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/25 text-purple-700 dark:text-purple-400 text-xs font-bold font-mono shadow-sm">
          <Cpu size={14} className="text-purple-500" />
          <span>HydraDB GraphBLAS · algo.MSpaths</span>
        </div>
        <h1 className="animate-fade-in-up stagger-2 text-2xl sm:text-4xl font-black text-slate-900 dark:text-white tracking-tight font-heading">
          Multi-Entity Path Retrieval
        </h1>
        <p className="animate-fade-in-up stagger-3 text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed max-w-xl mx-auto font-medium">
          Evaluates bounded paths across multiple source and target entities simultaneously using native matrix operations with reverse target pruning.
        </p>
      </div>

      {/* Query Bar */}
      <div className="space-y-3 max-w-3xl mx-auto animate-fade-in-up stagger-4">
        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2.5">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={entitiesInput}
              onChange={(e) => setEntitiesInput(e.target.value)}
              placeholder="Comma-separated entities (e.g., Alex, Dhaka, Tech Startup)..."
              className="input-field pl-11 pr-4 py-3 text-xs sm:text-sm shadow-sm w-full"
            />
          </div>
          <input
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            aria-label="User ID"
            placeholder="User ID"
            className="input-field w-full sm:w-28 py-3 text-xs font-mono"
          />
          <button
            type="submit"
            disabled={loading || !entitiesInput.trim()}
            className="btn-primary text-xs sm:text-sm px-6 py-3 flex items-center justify-center gap-2 flex-shrink-0 shadow-md bg-purple-600 hover:bg-purple-700 text-white border-purple-500"
          >
            {loading ? <RefreshCw size={14} className="animate-spin" /> : <Workflow size={14} />}
            <span>Query Paths</span>
          </button>
        </form>

        {/* Quick Suggestion Chips */}
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 font-medium pt-1">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-bold">Try:</span>
          {quickPresets.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setEntitiesInput(preset.entities);
                handleQuery(preset.entities);
              }}
              className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 dark:bg-white/[0.05] hover:bg-purple-500/10 hover:text-purple-600 dark:hover:text-purple-400 border border-slate-200 dark:border-white/[0.06] transition-all cursor-pointer"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/25 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2.5 max-w-3xl mx-auto animate-fade-in shadow-sm">
          <AlertTriangle size={16} className="flex-shrink-0" />
          <span className="font-semibold">{error}</span>
        </div>
      )}

      {/* Loading Skeleton State */}
      {loading && (
        <div className="p-12 rounded-3xl glass-card border border-slate-200 dark:border-white/[0.08] text-center space-y-4 max-w-3xl mx-auto animate-pulse">
          <div className="w-12 h-12 rounded-2xl bg-purple-500/20 mx-auto flex items-center justify-center text-purple-500">
            <RefreshCw size={24} className="animate-spin" />
          </div>
          <div className="space-y-2">
            <h3 className="text-sm font-bold text-slate-800 dark:text-white">Evaluating Multi-Entity Topology</h3>
            <p className="text-xs text-slate-500 font-mono">Running HydraDB algo.MSpaths bounded path expansion...</p>
          </div>
        </div>
      )}

      {/* Results View */}
      {!loading && data && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Metadata Summary Banner */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-white/70 dark:bg-[#0c1220]/70 border border-slate-200/80 dark:border-white/[0.08] backdrop-blur-xl shadow-sm">
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 rounded-xl text-xs font-mono font-bold bg-purple-500/15 text-purple-700 dark:text-purple-300 border border-purple-500/30 flex items-center gap-1.5">
                <CheckCircle2 size={13} />
                <span>{data.procedure}</span>
              </span>
              <span className="text-xs text-slate-600 dark:text-slate-400 font-medium">
                Entities Evaluated:{' '}
                <strong className="text-slate-900 dark:text-white font-mono">{data.entities.join(', ')}</strong>
              </span>
            </div>
            <div className="flex items-center gap-4 text-xs font-mono font-bold text-slate-500">
              <span>{data.paths_found} Paths Found</span>
              <span>{data.nodes.length} Graph Nodes</span>
              <span>{data.edges.length} Relationships</span>
            </div>
          </div>

          {/* Empty State */}
          {data.paths_found === 0 && (
            <div className="p-12 rounded-3xl glass-card border border-slate-200 dark:border-white/[0.08] text-center space-y-3 max-w-2xl mx-auto">
              <GitFork size={32} className="mx-auto text-slate-400 opacity-60" />
              <h3 className="text-sm font-bold text-slate-800 dark:text-white">No Connected Paths Discovered</h3>
              <p className="text-xs text-slate-500 leading-relaxed max-w-md mx-auto">
                HydraDB evaluated bounded paths up to length 5 between the specified entities, but no relationship paths or active fact chains currently connect them.
              </p>
            </div>
          )}

          {/* Graph & Paths Grid */}
          {data.paths_found > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Visual Subgraph Topology & Relationship Matrix */}
              <div className="lg:col-span-2 space-y-4">
                <div className="feature-card !p-5 space-y-4 shadow-md">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-white/[0.06]">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-white">
                      <Layers size={16} className="text-purple-500" />
                      <span>Bounded Subgraph Topology</span>
                    </div>
                    {/* Edge Legend */}
                    <div className="flex items-center gap-3 text-[10px] font-mono font-bold">
                      <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                        <span className="w-3.5 h-0.5 bg-emerald-500 rounded inline-block" />
                        MENTIONS
                      </span>
                      <span className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
                        <span className="w-3.5 h-0.5 bg-amber-500 border-b border-dashed border-amber-500 rounded inline-block" />
                        SUPERSEDES
                      </span>
                    </div>
                  </div>

                  {/* Connected Graph Visualization Canvas */}
                  <div className="p-6 rounded-2xl bg-slate-50 dark:bg-black/40 border border-slate-200 dark:border-white/[0.06] space-y-4">
                    <div className="flex flex-wrap items-center justify-center gap-3">
                      {data.nodes.map((node) => (
                        <div
                          key={node.id}
                          className={`px-3.5 py-2 rounded-xl text-xs font-medium border shadow-sm transition-all ${
                            node.type === 'Entity'
                              ? 'bg-purple-500/15 text-purple-800 dark:text-purple-200 border-purple-500/40 font-bold'
                              : node.data?.is_current === false
                              ? 'bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-500/30 line-through opacity-80'
                              : 'bg-emerald-500/15 text-emerald-900 dark:text-emerald-200 border-emerald-500/30'
                          }`}
                        >
                          <span className="text-[10px] font-mono uppercase opacity-75 mr-1.5">[{node.type}]</span>
                          {node.label}
                        </div>
                      ))}
                    </div>

                    {/* Edge Flow Summary */}
                    <div className="pt-4 border-t border-slate-200 dark:border-white/[0.06] space-y-2">
                      <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-bold block">
                        Relationships Traversed:
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {data.edges.map((edge, i) => {
                          const isSupersedes = edge.type === 'SUPERSEDES';
                          return (
                            <div
                              key={i}
                              className={`px-3 py-2 rounded-xl text-xs flex items-center justify-between border ${
                                isSupersedes
                                  ? 'bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-500/25 border-dashed'
                                  : 'bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border-emerald-500/20'
                              }`}
                            >
                              <span className="font-mono text-[11px] font-bold">
                                #{edge.source} → #{edge.target}
                              </span>
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-white/50 dark:bg-black/40">
                                {edge.type}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>

                {/* OpenCypher Code Display */}
                <div className="space-y-2">
                  <span className="section-label">
                    <Code2 size={13} className="text-purple-500" />
                    HydraDB OpenCypher algo.MSpaths Query
                  </span>
                  <div className="rounded-2xl overflow-hidden border border-slate-800 shadow-md">
                    <CodeViewer code={cypherQuerySnippet} language="opencypher" />
                  </div>
                </div>
              </div>

              {/* Right Column: Path Fact Chains with Timestamps */}
              <div className="space-y-4">
                <div className="feature-card !p-5 space-y-4 shadow-md">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-white/[0.06]">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-white">
                      <Clock size={16} className="text-blue-500" />
                      <span>Fact Chains & Timelines</span>
                    </div>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-lg bg-blue-500/10 text-blue-700 dark:text-blue-400">
                      {data.paths.length} Chain{data.paths.length === 1 ? '' : 's'}
                    </span>
                  </div>

                  {/* Path Selector Tabs */}
                  <div className="flex gap-1.5 overflow-x-auto pb-1">
                    {data.paths.map((p, idx) => (
                      <button
                        key={p.path_id}
                        onClick={() => setSelectedPathId(p.path_id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-mono font-bold transition-all cursor-pointer whitespace-nowrap ${
                          selectedPathId === p.path_id
                            ? 'bg-purple-600 text-white shadow-sm'
                            : 'bg-slate-100 dark:bg-white/[0.05] text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                        }`}
                      >
                        Path #{idx + 1} ({p.length} hops)
                      </button>
                    ))}
                  </div>

                  {/* Fact Chain Details */}
                  {data.paths
                    .filter((p) => !selectedPathId || p.path_id === selectedPathId)
                    .map((path) => (
                      <div key={path.path_id} className="space-y-3 pt-2 animate-fade-in">
                        <div className="text-xs text-slate-500 font-mono font-bold flex items-center justify-between">
                          <span>{path.start_entity}</span>
                          <ArrowRight size={13} className="text-purple-500" />
                          <span>{path.end_entity}</span>
                        </div>

                        {path.fact_chain.length === 0 ? (
                          <div className="p-4 rounded-xl bg-slate-50 dark:bg-black/20 text-xs text-slate-500 italic text-center">
                            Direct entity connection without intermediary facts.
                          </div>
                        ) : (
                          <div className="space-y-2.5">
                            {path.fact_chain.map((fact, fIdx) => (
                              <div
                                key={fIdx}
                                className={`p-3.5 rounded-xl border text-xs space-y-1.5 transition-all ${
                                  fact.is_current
                                    ? 'bg-emerald-500/[0.06] dark:bg-emerald-500/[0.04] border-emerald-500/30 text-emerald-950 dark:text-emerald-200'
                                    : 'bg-amber-500/[0.06] dark:bg-amber-500/[0.04] border-amber-500/30 text-amber-950 dark:text-amber-200'
                                }`}
                              >
                                <div className="flex items-center justify-between text-[10px] font-mono">
                                  <span className="font-bold uppercase tracking-wider">
                                    {fact.is_current ? 'Active Fact' : 'Superseded Fact'}
                                  </span>
                                  {fact.created_at && (
                                    <span className="text-slate-500 font-medium">
                                      {new Date(fact.created_at).toLocaleString(undefined, {
                                        month: 'short',
                                        day: 'numeric',
                                        hour: '2-digit',
                                        minute: '2-digit',
                                      })}
                                    </span>
                                  )}
                                </div>
                                <p className="font-semibold leading-relaxed">{fact.content}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
