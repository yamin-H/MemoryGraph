'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { Search, RotateCcw, Network } from 'lucide-react';

// Dynamically import with ssr:false — Three.js/WebGL requires browser APIs
const MemoryGraph = dynamic(
  () => import('@/components/MemoryGraph').then((mod) => mod.MemoryGraph),
  {
    ssr: false,
    loading: () => (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
        <div className="w-10 h-10 border-2 border-amber-500/40 border-t-amber-500 rounded-full animate-spin" />
        <span className="text-xs font-semibold font-mono text-slate-600 dark:text-slate-400">Loading 3D Knowledge Graph...</span>
      </div>
    ),
  }
);

export default function GraphExplorerPage() {
  const [searchInput, setSearchInput] = useState('');
  const [searchType, setSearchType] = useState<'entity' | 'session'>('entity');
  const [activeEntity, setActiveEntity] = useState<string | undefined>(undefined);
  const [activeSession, setActiveSession] = useState<string | undefined>(undefined);
  const [userId, setUserId] = useState('user');

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
    <div className="flex flex-col h-full bg-slate-100 dark:bg-[#090d16] transition-colors duration-200">
      {/* Top Search & Filter Bar */}
      <div className="px-6 py-3.5 border-b border-slate-200 dark:border-white/[0.08] bg-white/80 dark:bg-[#0c1220]/80 backdrop-blur-xl flex-shrink-0 z-10">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          {/* Search form */}
          <form onSubmit={handleSearch} className="flex items-center gap-2.5 flex-1 max-w-xl">
            <div className="flex rounded-xl bg-slate-100 dark:bg-black/40 border border-slate-200 dark:border-white/[0.08] p-1 flex-shrink-0">
              <button
                type="button"
                onClick={() => setSearchType('entity')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  searchType === 'entity'
                    ? 'bg-amber-500 text-slate-950 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              >
                Entity
              </button>
              <button
                type="button"
                onClick={() => setSearchType('session')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  searchType === 'session'
                    ? 'bg-amber-500 text-slate-950 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              >
                Session
              </button>
            </div>

            <div className="relative flex-1">
              <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder={
                  searchType === 'entity'
                    ? 'Search entity (e.g., Alex, Mochi, San Francisco)...'
                    : 'Search session ID (e.g., alex-session-1)...'
                }
                className="input-field pl-10 py-2 text-xs h-[38px] shadow-sm"
              />
            </div>

            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              aria-label="User ID"
              placeholder="User ID"
              className="input-field w-28 py-2 text-xs h-[38px] font-mono"
              required
            />

            <button type="submit" className="btn-primary text-xs h-[38px] px-4 flex-shrink-0 shadow-sm">
              Filter
            </button>

            {(activeEntity || activeSession) && (
              <button
                type="button"
                onClick={handleReset}
                className="p-2 rounded-xl bg-slate-100 dark:bg-white/[0.04] hover:bg-slate-200 dark:hover:bg-white/[0.08] border border-slate-200 dark:border-white/[0.08] text-slate-500 hover:text-slate-800 dark:hover:text-white transition-colors cursor-pointer"
                title="Reset View"
              >
                <RotateCcw size={15} />
              </button>
            )}
          </form>

          {/* Active target badge */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-600 dark:text-slate-400 font-mono font-medium px-3 py-1 rounded-xl bg-slate-100 dark:bg-white/[0.03] border border-slate-200 dark:border-white/[0.06] flex items-center gap-1.5">
              <Network size={12} className="text-amber-500" />
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
        <MemoryGraph entityName={activeEntity} sessionId={activeSession} userId={userId.trim() || 'user'} />
      </div>
    </div>
  );
}
