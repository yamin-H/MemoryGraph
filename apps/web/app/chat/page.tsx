'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ChatInterface } from '@/components/ChatInterface';
import { QueryResponse } from '@/lib/types';
import { ConfidenceScore } from '@/components/ConfidenceScore';
import {
  Terminal,
  Clock,
  Hash,
  Cpu,
  Layers,
  AlertTriangle,
  Swords,
  Sparkles,
} from 'lucide-react';

export default function ChatPage() {
  const [lastResponse, setLastResponse] = useState<QueryResponse | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(true);

  return (
    <div className="flex h-full overflow-hidden bg-slate-50 dark:bg-[#090d16] transition-colors duration-200">
      {/* Primary Chat Window */}
      <div className="flex-1 flex flex-col min-w-0 h-full">
        {/* Header bar */}
        <div className="px-6 py-3.5 border-b border-slate-200 dark:border-white/[0.08] bg-white/80 dark:bg-[#0c1220]/80 backdrop-blur-xl flex items-center justify-between flex-shrink-0">
          <div>
            <h1 className="text-sm font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2 font-heading">
              <Sparkles size={15} className="text-amber-500" />
              MemoryGraph Agent Interface
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Interactive temporal memory query & multi-session fact synthesizer
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Link
              href="/arena"
              className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-700 dark:text-amber-300 transition-colors shadow-sm"
            >
              <Swords size={13} className="text-amber-500 dark:text-amber-400" />
              <span>Battle Arena</span>
            </Link>

            <button
              onClick={() => setDetailsOpen(!detailsOpen)}
              className="hidden lg:flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-white/[0.04] hover:bg-slate-200 dark:hover:bg-white/[0.08] border border-slate-200 dark:border-white/[0.08] text-slate-700 dark:text-slate-300 hover:text-amber-600 dark:hover:text-amber-400 transition-colors cursor-pointer"
            >
              <Terminal size={13} />
              <span>{detailsOpen ? 'Hide Inspector' : 'Show Inspector'}</span>
            </button>
          </div>
        </div>

        {/* Chat Component */}
        <div className="flex-1 min-h-0">
          <ChatInterface onAnswerChange={(resp) => setLastResponse(resp)} />
        </div>
      </div>

      {/* Real-time Graph Retrieval Inspector Side Panel (Desktop) */}
      <div
        className={`hidden lg:flex flex-col border-l border-slate-200 dark:border-white/[0.08] bg-white/95 dark:bg-[#0c1220]/95 backdrop-blur-2xl transition-all duration-300 ease-in-out flex-shrink-0 shadow-xl lg:shadow-none ${
          detailsOpen ? 'w-96' : 'w-0 overflow-hidden'
        }`}
      >
        {detailsOpen && (
          <div className="flex flex-col h-full overflow-hidden">
            {/* Inspector Header */}
            <div className="p-4 border-b border-slate-200 dark:border-white/[0.08] flex items-center justify-between bg-slate-100/50 dark:bg-black/20">
              <div className="flex items-center gap-2">
                <Terminal size={15} className="text-amber-500 dark:text-amber-400" />
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200 font-mono">
                  Retrieval Inspector
                </h2>
              </div>
              <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 uppercase font-bold px-2 py-0.5 rounded bg-slate-200 dark:bg-white/[0.06]">
                {lastResponse ? 'Live Frame' : 'Standby'}
              </span>
            </div>

            {/* Inspector Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
              {lastResponse ? (
                <div className="space-y-4 animate-fade-in">
                  {/* Execution Metrics Grid */}
                  <div className="grid grid-cols-2 gap-2.5">
                    <div className="p-3 rounded-2xl bg-slate-100 dark:bg-slate-900/90 border border-slate-200 dark:border-white/[0.06] shadow-sm">
                      <div className="flex items-center gap-1 text-[10px] uppercase font-bold text-slate-500 mb-1 font-mono">
                        <Clock size={11} className="text-amber-500" /> Latency
                      </div>
                      <p className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100">
                        {lastResponse.query_time_ms} ms
                      </p>
                    </div>

                    <div className="p-3 rounded-2xl bg-slate-100 dark:bg-slate-900/90 border border-slate-200 dark:border-white/[0.06] shadow-sm">
                      <div className="flex items-center gap-1 text-[10px] uppercase font-bold text-slate-500 mb-1 font-mono">
                        <Layers size={11} className="text-blue-500" /> Facts Checked
                      </div>
                      <p className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100">
                        {lastResponse.facts_examined ?? 0} facts
                      </p>
                    </div>

                    <div className="p-3 rounded-2xl bg-slate-100 dark:bg-slate-900/90 border border-slate-200 dark:border-white/[0.06] shadow-sm">
                      <div className="flex items-center gap-1 text-[10px] uppercase font-bold text-slate-500 mb-1 font-mono">
                        <Cpu size={11} className="text-purple-500" /> LLM Tokens
                      </div>
                      <p className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100">
                        {lastResponse.groq_tokens_used ?? 0}
                      </p>
                    </div>

                    <div className="p-3 rounded-2xl bg-slate-100 dark:bg-slate-900/90 border border-slate-200 dark:border-white/[0.06] shadow-sm">
                      <div className="flex items-center gap-1 text-[10px] uppercase font-bold text-slate-500 mb-1 font-mono">
                        <Hash size={11} className="text-emerald-500" /> Confidence
                      </div>
                      <div className="mt-0.5">
                        <ConfidenceScore score={lastResponse.confidence} showLabel={false} size="sm" />
                      </div>
                    </div>
                  </div>

                  {/* Abstention Status */}
                  {lastResponse.abstained && (
                    <div className="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-1">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-amber-800 dark:text-amber-300">
                        <AlertTriangle size={14} />
                        <span>Abstention Decision</span>
                      </div>
                      <p className="text-xs text-amber-900 dark:text-amber-200/90 leading-relaxed font-medium">
                        {lastResponse.abstention_reason || 'Low fact confidence or missing historical data'}
                      </p>
                    </div>
                  )}

                  {/* Traversed Sessions */}
                  {lastResponse.source_sessions && lastResponse.source_sessions.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-mono">
                        Traversed Sessions
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {lastResponse.source_sessions.map((sess, i) => (
                          <span
                            key={i}
                            className="px-2.5 py-1 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-700 dark:text-blue-300 font-mono text-[11px] font-semibold"
                          >
                            {sess}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Superseded Facts */}
                  {lastResponse.superseded_facts && lastResponse.superseded_facts.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 font-mono">
                        Superseded Facts ({lastResponse.superseded_facts.length})
                      </span>
                      <div className="space-y-1.5">
                        {lastResponse.superseded_facts.map((fact, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs space-y-1 text-rose-900 dark:text-rose-200 font-medium"
                          >
                            <span className="text-[9px] font-mono text-rose-700 dark:text-rose-400 block font-bold">
                              FACT ID: {fact.fact_id}
                            </span>
                            <p>{fact.content}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Reasoning Trajectory */}
                  {lastResponse.reasoning && (
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-mono">
                        Graph Traversal Reasoning
                      </span>
                      <div className="p-3.5 rounded-2xl bg-slate-100 dark:bg-black/40 border border-slate-200 dark:border-white/[0.08] text-xs text-slate-800 dark:text-slate-300 font-mono leading-relaxed whitespace-pre-wrap">
                        {lastResponse.reasoning}
                      </div>
                    </div>
                  )}

                  {/* Raw JSON inspection */}
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-mono">
                      Raw Response Payload
                    </span>
                    <pre className="p-3.5 rounded-2xl bg-[#0b0f19] border border-slate-800 text-[11px] text-amber-300/90 font-mono overflow-x-auto max-h-48">
                      {JSON.stringify(lastResponse, null, 2)}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-center text-slate-500">
                  <Terminal size={26} className="mb-2 opacity-40" />
                  <p className="font-bold text-xs text-slate-700 dark:text-slate-300">Inspector on Standby</p>
                  <p className="text-xs text-slate-500 mt-1 max-w-[220px]">
                    Submit a query to inspect live graph traversal details and fact history.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}