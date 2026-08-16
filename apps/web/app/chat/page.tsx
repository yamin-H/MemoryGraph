'use client';

import { useState } from 'react';
import { ChatInterface } from '@/components/ChatInterface';
import { QueryResponse } from '@/lib/types';
import { ConfidenceScore } from '@/components/ConfidenceScore';
import { Code, Terminal, Clock, Hash, Cpu, Layers, ChevronRight, ChevronLeft, Info, AlertTriangle } from 'lucide-react';

export default function ChatPage() {
  const [lastResponse, setLastResponse] = useState<QueryResponse | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(true);

  return (
    <div className="flex h-full overflow-hidden bg-[#080b11]">
      {/* Primary Chat Window */}
      <div className="flex-1 flex flex-col min-w-0 h-full">
        {/* Header bar */}
        <div className="px-6 py-3.5 border-b border-white/[0.08] bg-[#0d121c]/80 flex items-center justify-between flex-shrink-0">
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              MemoryGraph Agent Interface
            </h1>
            <p className="text-[11px] text-slate-400">
              Interactive temporal memory query & multi-session fact synthesizer
            </p>
          </div>

          <button
            onClick={() => setDetailsOpen(!detailsOpen)}
            className="hidden lg:flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 hover:text-amber-400 transition-colors"
          >
            <Terminal size={13} />
            <span>{detailsOpen ? 'Hide Inspector' : 'Show Inspector'}</span>
          </button>
        </div>

        {/* Chat Component */}
        <div className="flex-1 min-h-0">
          <ChatInterface onAnswerChange={(resp) => setLastResponse(resp)} />
        </div>
      </div>

      {/* Real-time Graph Retrieval Inspector Side Panel (Desktop) */}
      <div
        className={`hidden lg:flex flex-col border-l border-white/[0.08] bg-[#0d121c]/95 transition-all duration-300 ease-in-out flex-shrink-0 ${
          detailsOpen ? 'w-96' : 'w-0 overflow-hidden'
        }`}
      >
        {detailsOpen && (
          <div className="flex flex-col h-full overflow-hidden">
            {/* Inspector Header */}
            <div className="p-4 border-b border-white/[0.08] flex items-center justify-between bg-black/20">
              <div className="flex items-center gap-2">
                <Terminal size={15} className="text-amber-400" />
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Retrieval Inspector
                </h2>
              </div>
              <span className="text-[10px] font-mono text-slate-500 uppercase">
                {lastResponse ? 'Live Frame' : 'Standby'}
              </span>
            </div>

            {/* Inspector Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
              {lastResponse ? (
                <div className="space-y-4 animate-[fadeIn_0.2s_ease-out]">
                  {/* Execution Metrics Grid */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-3 rounded-xl bg-slate-900/90 border border-white/[0.06]">
                      <div className="flex items-center gap-1 text-[10px] uppercase font-bold text-slate-500 mb-1">
                        <Clock size={11} className="text-amber-400" /> Latency
                      </div>
                      <p className="text-sm font-bold font-mono text-slate-200">
                        {lastResponse.query_time_ms} ms
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900/90 border border-white/[0.06]">
                      <div className="flex items-center gap-1 text-[10px] uppercase font-bold text-slate-500 mb-1">
                        <Layers size={11} className="text-blue-400" /> Facts Checked
                      </div>
                      <p className="text-sm font-bold font-mono text-slate-200">
                        {lastResponse.facts_examined ?? 0} facts
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900/90 border border-white/[0.06]">
                      <div className="flex items-center gap-1 text-[10px] uppercase font-bold text-slate-500 mb-1">
                        <Cpu size={11} className="text-purple-400" /> LLM Tokens
                      </div>
                      <p className="text-sm font-bold font-mono text-slate-200">
                        {lastResponse.groq_tokens_used ?? 0}
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900/90 border border-white/[0.06]">
                      <div className="flex items-center gap-1 text-[10px] uppercase font-bold text-slate-500 mb-1">
                        <Hash size={11} className="text-emerald-400" /> Confidence
                      </div>
                      <div className="mt-0.5">
                        <ConfidenceScore score={lastResponse.confidence} showLabel={false} size="sm" />
                      </div>
                    </div>
                  </div>

                  {/* Abstention Status */}
                  {lastResponse.abstained && (
                    <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 space-y-1">
                      <div className="flex items-center gap-1.5 text-[11px] font-bold text-amber-300">
                        <AlertTriangle size={13} />
                        <span>Abstention Decision</span>
                      </div>
                      <p className="text-[11px] text-amber-200/90 leading-relaxed">
                        {lastResponse.abstention_reason || 'Low fact confidence or missing historical data'}
                      </p>
                    </div>
                  )}

                  {/* Traversed Sessions */}
                  {lastResponse.source_sessions && lastResponse.source_sessions.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        Traversed Sessions
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {lastResponse.source_sessions.map((sess, i) => (
                          <span
                            key={i}
                            className="px-2 py-1 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-300 font-mono text-[11px]"
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
                      <span className="text-[10px] font-bold uppercase tracking-wider text-rose-400">
                        Superseded Facts ({lastResponse.superseded_facts.length})
                      </span>
                      <div className="space-y-1.5">
                        {lastResponse.superseded_facts.map((fact, idx) => (
                          <div
                            key={idx}
                            className="p-2.5 rounded-lg bg-rose-500/[0.07] border border-rose-500/20 text-[11px] space-y-1 text-rose-200"
                          >
                            <span className="text-[9px] font-mono text-rose-400 block font-semibold">
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
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        Graph Traversal Reasoning
                      </span>
                      <div className="p-3 rounded-xl bg-black/40 border border-white/[0.08] text-[11px] text-slate-300 font-mono leading-relaxed whitespace-pre-wrap">
                        {lastResponse.reasoning}
                      </div>
                    </div>
                  )}

                  {/* Raw JSON inspection */}
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      Raw Response Payload
                    </span>
                    <pre className="p-3 rounded-xl bg-black/60 border border-white/[0.08] text-[10px] text-amber-300/80 font-mono overflow-x-auto max-h-48">
                      {JSON.stringify(lastResponse, null, 2)}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-center text-slate-500">
                  <Terminal size={24} className="mb-2 opacity-40" />
                  <p className="font-semibold text-xs text-slate-400">Inspector on Standby</p>
                  <p className="text-[11px] text-slate-500 mt-1 max-w-[200px]">
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