'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { Search, RotateCcw } from 'lucide-react';

// Dynamically import with ssr:false — Three.js/WebGL requires browser APIs
const MemoryGraph = dynamic(
  () => import('@/components/MemoryGraph').then((mod) => mod.MemoryGraph),
  {
    ssr: false,
    loading: () => (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
        <div className="w-8 h-8 border-2 border-amber-500/40 border-t-amber-500 rounded-full animate-spin" />
        <span className="text-sm">Loading 3D Knowledge Graph...</span>
      </div>
    ),
  }
);

export default function GraphExplorerPage() {
  const [searchInput, setSearchInput] = useState('');
  const [searchType, setSearchType] = useState<'entity' | 'session'>('entity');
  const [activeEntity, setActiveEntity] = useState<string | undefined>(undefined);
  const [activeSession, setActiveSession] = useState<string | undefined>(undefined);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const query = searchInput.trim();
    if (!query) {
      handleReset();
      return;
    }

    if (searchType === 'entity') {
      setActiveEntity(query);
      setActiveSession(undefined);
    } else {
      setActiveSession(query);
      setActiveEntity(undefined);
    }
  };

  const handleReset = () => {
    setSearchInput('');
    setActiveEntity(undefined);
    setActiveSession(undefined);
  };

  return (
    <div className="flex flex-col h-full bg-[#080b11]">
      {/* Top Search & Filter Bar */}
      <div className="px-6 py-3 border-b border-white/[0.08] bg-[#0d121c]/80 backdrop-blur-xl flex-shrink-0 z-10">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          {/* Search form */}
          <form onSubmit={handleSearch} className="flex items-center gap-2 flex-1 max-w-xl">
            <div className="flex rounded-lg bg-black/40 border border-white/[0.08] p-0.5 flex-shrink-0">
              <button
                type="button"
                onClick={() => setSearchType('entity')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                  searchType === 'entity'
                    ? 'bg-amber-500 text-slate-950 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Entity
              </button>
              <button
                type="button"
                onClick={() => setSearchType('session')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                  searchType === 'session'
                    ? 'bg-amber-500 text-slate-950 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Session
              </button>
            </div>

            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder={
                  searchType === 'entity'
                    ? 'Search entity (e.g., Alex, Mochi, San Francisco)...'
                    : 'Search session ID (e.g., alex-session-1)...'
                }
                className="input-field pl-9 py-1.5 text-xs h-[36px]"
              />
            </div>

            <button type="submit" className="btn-primary text-xs h-[36px] px-3.5 flex-shrink-0">
              Filter
            </button>

            {(activeEntity || activeSession) && (
              <button
                type="button"
                onClick={handleReset}
                className="p-2 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-400 hover:text-white"
                title="Reset View"
              >
                <RotateCcw size={14} />
              </button>
            )}
          </form>

          {/* Active target badge */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-400 font-mono">
              {activeEntity
                ? `Entity: "${activeEntity}"`
                : activeSession
                ? `Session: "${activeSession}"`
                : 'Full Knowledge Graph (All Nodes)'}
            </span>
          </div>
        </div>
      </div>

      {/* 3D Visualizer Canvas */}
      <div className="flex-1 min-h-0 relative">
        <MemoryGraph entityName={activeEntity} sessionId={activeSession} />
      </div>
    </div>
  );
}