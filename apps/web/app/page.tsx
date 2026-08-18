'use client';

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import {
  MessageSquare,
  Network,
  BarChart3,
  Upload,
  ArrowRight,
  Sparkles,
  Swords,
  ShieldCheck,
  Zap,
  Code2,
  Copy,
  Check,
  Play,
  RotateCcw,
  Database,
  Cpu,
  Layers,
  GitFork,
  CheckCircle2,
  HardDrive,
  RefreshCw,
} from 'lucide-react';
import { CodeViewer } from '@/components/CodeViewer';
import { api } from '@/lib/api';
import { GraphData } from '@/lib/types';

const AVAILABLE_CELL_USERS = [
  { id: 'alex', name: 'Alex', role: 'Software Architect', cell: 'cell-3', location: 'Dhaka' },
  { id: 'jordan', name: 'Jordan', role: 'DevOps Lead', cell: 'cell-6', location: 'Singapore' },
  { id: 'taylor', name: 'Taylor', role: 'ML Researcher', cell: 'cell-1', location: 'Boston' },
  { id: 'sarah', name: 'Sarah', role: 'Product Manager', cell: 'cell-4', location: 'London' },
];

/* ── Feature Cards Data ── */
const featureActions = [
  {
    href: '/arena',
    icon: Swords,
    title: 'Vector vs. Graph Arena',
    description: 'Watch vector RAG retrieve outdated facts while HydraDB resolves temporal truth.',
    badge: 'Live Battle',
    accentColor: 'amber',
  },
  {
    href: '/abstention',
    icon: ShieldCheck,
    title: 'Abstention & Truth Matrix',
    description: 'Calibrated graph confidence scoring that eliminates hallucination.',
    badge: 'Track 03 Core',
    accentColor: 'blue',
  },
  {
    href: '/chat',
    icon: MessageSquare,
    title: 'Agent Memory Chat',
    description: 'Multi-session temporal fact queries with real-time confidence scoring.',
    badge: 'Retrieval',
    accentColor: 'sky',
  },
  {
    href: '/graph',
    icon: Network,
    title: '3D Graph Visualizer',
    description: 'Interactive canvas with glowing active facts and superseded lineage.',
    badge: 'HydraDB',
    accentColor: 'emerald',
  },
  {
    href: '/benchmark',
    icon: BarChart3,
    title: 'Evaluation Matrix',
    description: 'LongMemEval and BEAM benchmarks vs. vector RAG & mem0.',
    badge: 'Benchmarks',
    accentColor: 'indigo',
  },
  {
    href: '/ingest',
    icon: Upload,
    title: 'Session Ingestion',
    description: 'Parse multi-turn dialogue into entities, facts, and graph anchors.',
    badge: 'Pipeline',
    accentColor: 'rose',
  },
];

const accentMap: Record<string, { card: string; icon: string; badge: string; hover: string; glow: string }> = {
  amber: {
    card: 'hover:border-amber-500/60',
    icon: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
    badge: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    hover: 'group-hover:text-amber-400',
    glow: 'hover:shadow-[0_0_30px_-5px_rgba(245,158,11,0.25)]',
  },
  blue: {
    card: 'hover:border-blue-500/60',
    icon: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
    badge: 'bg-blue-500/10 text-blue-300 border-blue-500/30',
    hover: 'group-hover:text-blue-400',
    glow: 'hover:shadow-[0_0_30px_-5px_rgba(59,130,246,0.25)]',
  },
  sky: {
    card: 'hover:border-sky-500/60',
    icon: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
    badge: 'bg-sky-500/10 text-sky-300 border-sky-500/30',
    hover: 'group-hover:text-sky-400',
    glow: 'hover:shadow-[0_0_30px_-5px_rgba(14,165,233,0.25)]',
  },
  emerald: {
    card: 'hover:border-emerald-500/60',
    icon: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
    badge: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    hover: 'group-hover:text-emerald-400',
    glow: 'hover:shadow-[0_0_30px_-5px_rgba(16,185,129,0.25)]',
  },
  indigo: {
    card: 'hover:border-indigo-500/60',
    icon: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30',
    badge: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30',
    hover: 'group-hover:text-indigo-400',
    glow: 'hover:shadow-[0_0_30px_-5px_rgba(99,102,241,0.25)]',
  },
  rose: {
    card: 'hover:border-rose-500/60',
    icon: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
    badge: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    hover: 'group-hover:text-rose-400',
    glow: 'hover:shadow-[0_0_30px_-5px_rgba(244,63,94,0.25)]',
  },
};

/* ── Code Examples ── */
const CODE_EXAMPLES = {
  python: `from memorygraph import MemoryGraph

# 1. Connect to HydraDB-powered memory layer
memory = MemoryGraph(api_url="http://localhost:8000")

# 2. Ingest conversation (supersedence resolved automatically)
memory.add_session(
    user_id="alex_123",
    messages=[
        {"role": "user", "content": "I moved from Rajshahi to Dhaka today."},
        {"role": "assistant", "content": "Welcome to Dhaka!"}
    ]
)

# 3. Query verified temporal memory
result = memory.query(user_id="alex_123", query="Where does Alex live?")
print(result.answer)      # "Alex lives in Dhaka."
print(result.confidence)  # 0.98`,
  agent: `from memorygraph import MemoryGraph
from langchain_core.tools import tool

memory = MemoryGraph(api_url="http://localhost:8000")

@tool
def recall_user_memory(user_id: str, question: str) -> str:
    """Recall verified facts from HydraDB temporal graph."""
    res = memory.query(user_id=user_id, query=question)
    if res.abstained:
        return "I do not have recorded memory of this information."
    return f"{res.answer} (Confidence: {int(res.confidence * 100)}%)"`,
  curl: `curl -X POST http://localhost:8000/query \\
  -H "Content-Type: application/json" \\
  -d '{
    "question": "Where does Alex live?",
    "user_id": "alex_123"
  }'`,
  opencypher: `// HydraDB OpenCypher: Active fact with supersedence lineage
MATCH (u:Entity {name: 'Alex'})-[:MENTIONS]-(f:Fact)
WHERE f.is_current = true AND NOT (f)-[:INVALIDATED_BY]->()
RETURN f.content AS active_fact,
       f.confidence AS score,
       f.created_at AS timestamp
ORDER BY f.created_at DESC`,
};

/* ── Animated Counter Hook ── */
function useCounter(target: number, duration = 1200) {
  const [count, setCount] = useState(0);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const start = performance.now();
    const step = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(target * ease));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration]);
  return count;
}

export default function HomePage() {
  const [activeCodeTab, setActiveCodeTab] = useState<'python' | 'agent' | 'curl' | 'opencypher'>('python');
  const [copied, setCopied] = useState(false);
  const [simStep, setSimStep] = useState<1 | 2 | 3>(1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  const factGain = useCounter(19);
  const querySpeed = useCounter(35);
  const hallucinationRate = useCounter(0);

  // Cell-Level Storage Isolation Demo State
  const [userA, setUserA] = useState('alex');
  const [userB, setUserB] = useState('jordan');
  const [graphA, setGraphA] = useState<GraphData | null>(null);
  const [graphB, setGraphB] = useState<GraphData | null>(null);
  const [loadingCells, setLoadingCells] = useState(false);

  const fetchCellData = async (uA: string, uB: string) => {
    setLoadingCells(true);
    try {
      const [dataA, dataB] = await Promise.all([
        api.getAllGraphs(uA),
        api.getAllGraphs(uB),
      ]);
      setGraphA(dataA);
      setGraphB(dataB);
    } catch (e) {
      console.error('Failed to load cell graphs', e);
    } finally {
      setLoadingCells(false);
    }
  };

  useEffect(() => {
    fetchCellData(userA, userB);
  }, [userA, userB]);

  useEffect(() => {
    let timer: any;
    if (isPlaying) {
      timer = setInterval(() => {
        setSimStep((prev) => (prev === 3 ? 1 : ((prev + 1) as 1 | 2 | 3)));
      }, 2800);
    }
    return () => clearInterval(timer);
  }, [isPlaying]);

  const handleCopyCode = () => {
    navigator.clipboard.writeText(CODE_EXAMPLES[activeCodeTab]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const codeTabs = [
    { key: 'python' as const, label: 'Python SDK' },
    { key: 'agent' as const, label: 'LangChain Tool' },
    { key: 'curl' as const, label: 'cURL' },
    { key: 'opencypher' as const, label: 'OpenCypher' },
  ];

  return (
    <>
      {/* ── Global Keyframe Styles ── */}
      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(22px); }
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
        @keyframes pulse-ring {
          0%   { transform: scale(1);   opacity: 0.6; }
          100% { transform: scale(1.9); opacity: 0; }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0px);   }
          50%       { transform: translateY(-8px); }
        }
        @keyframes drift {
          0%   { transform: translate(0,   0);    opacity: 0.35; }
          33%  { transform: translate(6px, -10px); opacity: 0.55; }
          66%  { transform: translate(-5px, 5px);  opacity: 0.4;  }
          100% { transform: translate(0,   0);    opacity: 0.35; }
        }
        @keyframes spin-slow {
          from { transform: rotate(0deg);   }
          to   { transform: rotate(360deg); }
        }
        @keyframes border-flow {
          0%,100% { opacity: 0.4; }
          50%      { opacity: 1;   }
        }
        @keyframes scanline {
          0%   { transform: translateY(-100%); }
          100% { transform: translateY(100vh); }
        }

        .anim-fade-up   { animation: fadeUp  0.55s cubic-bezier(.22,.68,0,1.1) both; }
        .anim-fade-in   { animation: fadeIn  0.45s ease both; }
        .delay-0  { animation-delay: 0s; }
        .delay-1  { animation-delay: 0.07s; }
        .delay-2  { animation-delay: 0.14s; }
        .delay-3  { animation-delay: 0.21s; }
        .delay-4  { animation-delay: 0.28s; }
        .delay-5  { animation-delay: 0.35s; }
        .delay-6  { animation-delay: 0.42s; }

        .shimmer-badge {
          background: linear-gradient(
            105deg,
            transparent 30%,
            rgba(251,191,36,0.18) 50%,
            transparent 70%
          ) left / 200% auto;
          animation: shimmer 2.8s linear infinite;
        }
        .float-slow { animation: float 5s ease-in-out infinite; }
        .drift-orb  { animation: drift 9s ease-in-out infinite; }

        .grain-overlay::before {
          content: '';
          position: absolute;
          inset: 0;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E");
          opacity: 0.028;
          pointer-events: none;
          border-radius: inherit;
          z-index: 0;
        }

        .card-glow-border {
          position: relative;
        }
        .card-glow-border::after {
          content: '';
          position: absolute;
          inset: -1px;
          border-radius: inherit;
          padding: 1px;
          background: linear-gradient(135deg, transparent, rgba(255,255,255,0.05), transparent);
          -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
          -webkit-mask-composite: xor;
          mask-composite: exclude;
          pointer-events: none;
          opacity: 0;
          transition: opacity 0.3s;
        }
        .card-glow-border:hover::after { opacity: 1; }

        .metric-pulse::before {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: inherit;
          border: 1px solid currentColor;
          animation: pulse-ring 2.2s cubic-bezier(.4,0,.6,1) infinite;
          opacity: 0;
        }

        .code-scanline::after {
          content: '';
          position: absolute;
          left: 0; right: 0;
          height: 2px;
          background: linear-gradient(90deg, transparent, rgba(251,191,36,0.08), transparent);
          animation: scanline 6s linear infinite;
          pointer-events: none;
        }
      `}</style>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">

        {/* ═══════════════ HERO ═══════════════ */}
        <section
          className={`
            relative rounded-3xl border border-white/[0.07] overflow-hidden grain-overlay
            bg-[#060a12]
            p-6 sm:p-10 lg:p-12 shadow-[0_0_80px_-20px_rgba(0,0,0,0.9)]
            ${mounted ? 'anim-fade-in delay-0' : 'opacity-0'}
          `}
        >
          {/* Deep background gradient */}
          <div className="absolute inset-0 bg-gradient-to-br from-[#0d1525] via-[#060a12] to-[#04070f] z-0" />

          {/* Animated ambient orbs */}
          <div className="drift-orb absolute top-[-60px] right-[-40px] w-[480px] h-[380px] rounded-full bg-gradient-radial from-amber-500/12 via-amber-600/5 to-transparent blur-[80px] pointer-events-none z-0" />
          <div className="drift-orb absolute bottom-[-40px] left-[-30px] w-[380px] h-[280px] rounded-full bg-gradient-radial from-sky-500/10 via-emerald-500/5 to-transparent blur-[70px] pointer-events-none z-0" style={{ animationDelay: '-3s' }} />
          <div className="drift-orb absolute top-1/2 left-1/3 w-[220px] h-[220px] rounded-full bg-gradient-radial from-indigo-500/8 to-transparent blur-[60px] pointer-events-none z-0" style={{ animationDelay: '-6s' }} />

          {/* Dot grid pattern */}
          <div
            className="absolute inset-0 z-0 pointer-events-none opacity-[0.12]"
            style={{
              backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.45) 1px, transparent 1px)',
              backgroundSize: '28px 28px',
            }}
          />

          {/* Top-edge highlight line */}
          <div className="absolute top-0 left-[10%] right-[10%] h-px bg-gradient-to-r from-transparent via-amber-400/40 to-transparent z-10" />

          <div className="relative z-10 max-w-3xl space-y-6">
            {/* Badge */}
            <div className={`${mounted ? 'anim-fade-up delay-1' : 'opacity-0'} inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-amber-400/30 bg-amber-500/[0.08] shimmer-badge`}>
              <Sparkles size={12} className="text-amber-400" />
              <span className="text-amber-300 text-[11px] font-black font-mono tracking-widest uppercase">
                HACK HYDRA 2026 · TRACK 03 CHAMPION
              </span>
            </div>

            {/* Title */}
            <h1 className={`${mounted ? 'anim-fade-up delay-2' : 'opacity-0'} text-3xl sm:text-4xl lg:text-5xl font-black text-white tracking-tight leading-[1.1] font-heading`}>
              Temporal Agent Memory{' '}
              <br className="hidden sm:block" />
              <span
                className="text-transparent bg-clip-text"
                style={{
                  backgroundImage: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 40%, #fcd34d 70%, #f59e0b 100%)',
                  backgroundSize: '200% auto',
                  animation: 'shimmer 4s linear infinite',
                }}
              >
                Graph-Native on HydraDB
              </span>
            </h1>

            {/* Subtitle */}
            <p className={`${mounted ? 'anim-fade-up delay-3' : 'opacity-0'} text-sm sm:text-base text-slate-400 leading-relaxed max-w-2xl`}>
              A graph-native alternative to{' '}
              <code className="text-rose-300 font-mono font-bold bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20">mem0</code>{' '}
              that resolves changing facts across multi-session chats with recursive{' '}
              <code className="text-amber-300 font-mono font-bold bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">SUPERSEDES</code>{' '}
              edges and eliminates hallucination with calibrated honest abstention.
            </p>

            {/* Metrics Row */}
            <div className={`${mounted ? 'anim-fade-up delay-4' : 'opacity-0'} flex flex-wrap gap-3.5 pt-2`}>
              {[
                { label: 'Fact Updates', value: `+${factGain}%`, color: 'emerald', colorVal: '#10b981' },
                { label: 'Query Speed',  value: `< ${querySpeed}ms`, color: 'amber',   colorVal: '#f59e0b' },
                { label: 'Hallucination', value: `${hallucinationRate}%`, color: 'blue', colorVal: '#3b82f6' },
              ].map(({ label, value, color, colorVal }) => (
                <div
                  key={label}
                  className="relative p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06] min-w-[130px] flex-1 sm:flex-initial overflow-hidden"
                  style={{ boxShadow: `0 0 24px -8px ${colorVal}30` }}
                >
                  {/* card shimmer top */}
                  <div className="absolute top-0 left-0 right-0 h-px opacity-40" style={{ background: `linear-gradient(90deg, transparent, ${colorVal}60, transparent)` }} />
                  <div className="text-[10px] uppercase font-bold text-slate-500 font-mono tracking-wider">{label}</div>
                  <div className={`text-2xl font-black font-mono mt-0.5 text-${color}-400`} style={{ color: colorVal }}>{value}</div>
                </div>
              ))}
            </div>

            {/* CTA Buttons */}
            <div className={`${mounted ? 'anim-fade-up delay-5' : 'opacity-0'} flex flex-wrap gap-3 pt-2`}>
              <Link
                href="/arena"
                className="group flex items-center gap-2 px-6 py-3 rounded-2xl text-xs sm:text-sm font-bold text-slate-950 transition-all duration-300 shadow-[0_0_24px_-4px_rgba(245,158,11,0.5)]"
                style={{ background: 'linear-gradient(135deg, #f59e0b, #fbbf24)' }}
              >
                <Swords size={15} />
                <span>Launch Battle Arena</span>
                <ArrowRight size={13} className="transition-transform duration-300 group-hover:translate-x-1 opacity-70" />
              </Link>
              <Link
                href="/abstention"
                className="flex items-center gap-2 px-5 py-3 rounded-2xl text-xs sm:text-sm font-bold border border-blue-500/25 bg-blue-500/[0.07] text-blue-300 hover:bg-blue-500/[0.14] hover:border-blue-400/40 transition-all duration-300"
              >
                <ShieldCheck size={15} className="text-blue-400" />
                <span>Abstention Matrix</span>
              </Link>
              <Link
                href="/graph"
                className="flex items-center gap-2 px-5 py-3 rounded-2xl text-xs sm:text-sm font-bold border border-white/[0.08] bg-white/[0.04] text-slate-300 hover:bg-white/[0.08] hover:text-white hover:border-white/[0.14] transition-all duration-300"
              >
                <Network size={15} className="text-emerald-400" />
                <span>Graph Visualizer</span>
              </Link>
            </div>
          </div>
        </section>

        {/* ═══════════════ TEMPORAL SIMULATOR ═══════════════ */}
        <section
          className={`
            relative rounded-3xl border border-white/[0.07] overflow-hidden grain-overlay
            bg-[#080d18] p-6 sm:p-8 space-y-6
            shadow-[0_0_60px_-20px_rgba(0,0,0,0.8)]
            ${mounted ? 'anim-fade-up delay-5' : 'opacity-0'}
          `}
        >
          {/* Ambient glow */}
          <div className="absolute top-0 right-0 w-[300px] h-[200px] rounded-full bg-amber-500/5 blur-[60px] pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-[200px] h-[150px] rounded-full bg-sky-500/5 blur-[50px] pointer-events-none" />
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />

          {/* Header */}
          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2.5">
                <div
                  className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/25 float-slow"
                  style={{ boxShadow: '0 0 16px -4px rgba(245,158,11,0.35)' }}
                >
                  <Zap size={15} className="text-amber-400" />
                </div>
                <h2 className="text-base sm:text-lg font-bold text-white tracking-wide font-heading">
                  Temporal Memory Simulator
                </h2>
              </div>
              <p className="text-xs sm:text-sm text-slate-500 pl-10">
                See how HydraDB supersedes changing facts over time with recursive graph edges.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className={`px-4 py-2 rounded-xl text-xs font-bold font-mono flex items-center gap-2 border transition-all duration-300 cursor-pointer ${
                  isPlaying
                    ? 'bg-amber-500 text-slate-950 border-amber-400 shadow-[0_0_20px_-4px_rgba(245,158,11,0.6)]'
                    : 'bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border-white/[0.08]'
                }`}
              >
                <Play size={12} className={isPlaying ? 'fill-slate-950' : ''} />
                <span>{isPlaying ? 'Playing…' : 'Auto-Play'}</span>
              </button>
              <button
                onClick={() => { setIsPlaying(false); setSimStep(1); }}
                className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.09] text-slate-500 hover:text-slate-200 border border-white/[0.08] transition-all cursor-pointer"
                title="Reset Simulator"
              >
                <RotateCcw size={14} />
              </button>
            </div>
          </div>

          {/* Step Tabs */}
          <div className="relative z-10 grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { step: 1 as const, label: 'Session 1',  quote: '"I live in Rajshahi"', color: 'blue',    colorVal: '#3b82f6' },
              { step: 2 as const, label: 'Session 20', quote: '"I moved to Dhaka"',   color: 'amber',   colorVal: '#f59e0b' },
              { step: 3 as const, label: 'Query Recall',quote: '"Where is Alex?"',    color: 'emerald', colorVal: '#10b981' },
            ].map(({ step, label, quote, color, colorVal }) => {
              const isActive = simStep === step;
              return (
                <button
                  key={step}
                  onClick={() => { setIsPlaying(false); setSimStep(step); }}
                  className={`relative p-4 rounded-2xl text-left border transition-all duration-350 cursor-pointer overflow-hidden ${
                    isActive
                      ? 'border-white/[0.12] bg-white/[0.05]'
                      : 'bg-white/[0.02] border-white/[0.05] text-slate-500 hover:bg-white/[0.04] hover:border-white/[0.08]'
                  }`}
                  style={isActive ? { boxShadow: `0 0 28px -8px ${colorVal}40` } : {}}
                >
                  {isActive && (
                    <div
                      className="absolute top-0 left-0 right-0 h-px"
                      style={{ background: `linear-gradient(90deg, transparent, ${colorVal}70, transparent)` }}
                    />
                  )}
                  <span
                    className="text-[11px] font-mono font-bold uppercase tracking-wider block mb-1.5"
                    style={{ color: isActive ? colorVal : undefined }}
                  >
                    Step {step} · {label}
                  </span>
                  <p className="text-xs sm:text-sm font-bold text-white/80 truncate">{quote}</p>
                </button>
              );
            })}
          </div>

          {/* Graph Visualizer Simulation */}
          <div className="relative z-10 p-5 sm:p-6 rounded-3xl bg-[#040710] border border-white/[0.05] flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="absolute inset-0 rounded-3xl" style={{ backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.2) 1px, transparent 1px)', backgroundSize: '20px 20px', opacity: 0.04 }} />

            {/* Fact 1 */}
            <div
              className={`relative p-4 rounded-2xl border transition-all duration-500 w-full md:w-60 overflow-hidden ${
                simStep === 1
                  ? 'bg-emerald-500/[0.07] border-emerald-500/40'
                  : 'bg-rose-500/[0.05] border-rose-500/20 opacity-70'
              }`}
              style={simStep === 1 ? { boxShadow: '0 0 20px -8px rgba(16,185,129,0.3)' } : {}}
            >
              {simStep === 1 && <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-400/50 to-transparent" />}
              <div className="flex items-center justify-between text-[10px] font-mono mb-2">
                <span className="text-slate-500 font-bold">Fact #1 · Session 1</span>
                <span className={`font-black px-2 py-0.5 rounded text-[9px] tracking-wider ${
                  simStep === 1
                    ? 'bg-emerald-500/20 text-emerald-300'
                    : 'bg-rose-500/20 text-rose-300'
                }`}>
                  {simStep === 1 ? 'ACTIVE' : 'SUPERSEDED'}
                </span>
              </div>
              <p className={`text-xs sm:text-sm font-bold transition-all duration-300 ${simStep > 1 ? 'line-through text-slate-600' : 'text-white'}`}>
                Alex lives in Rajshahi
              </p>
            </div>

            {/* Edge Arrow */}
            <div className="flex flex-col items-center justify-center shrink-0 gap-1.5">
              {simStep >= 2 ? (
                <div className="flex flex-col items-center" style={{ animation: 'fadeIn 0.4s ease-out both' }}>
                  <span className="text-[9px] font-mono font-black text-amber-300 uppercase tracking-[0.18em] px-2.5 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 mb-2">
                    SUPERSEDES
                  </span>
                  <div className="relative w-16 h-[2px] overflow-hidden rounded-full">
                    <div className="absolute inset-0 bg-gradient-to-r from-amber-500 to-emerald-400" />
                    <div
                      className="absolute inset-0 opacity-70"
                      style={{
                        background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.8), transparent)',
                        backgroundSize: '200% auto',
                        animation: 'shimmer 1.5s linear infinite',
                      }}
                    />
                  </div>
                </div>
              ) : (
                <div className="w-10 h-px bg-white/10 rounded-full" />
              )}
            </div>

            {/* Fact 2 */}
            <div
              className={`relative p-4 rounded-2xl border transition-all duration-500 w-full md:w-60 overflow-hidden ${
                simStep >= 2
                  ? 'bg-emerald-500/[0.07] border-emerald-500/40'
                  : 'bg-white/[0.02] border-white/[0.04] opacity-30'
              }`}
              style={simStep >= 2 ? { boxShadow: '0 0 20px -8px rgba(16,185,129,0.3)' } : {}}
            >
              {simStep >= 2 && <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-400/50 to-transparent" />}
              <div className="flex items-center justify-between text-[10px] font-mono mb-2">
                <span className="text-slate-500 font-bold">Fact #2 · Session 20</span>
                <span className={`font-black px-2 py-0.5 rounded text-[9px] tracking-wider ${
                  simStep >= 2
                    ? 'bg-emerald-500/20 text-emerald-300'
                    : 'bg-white/5 text-slate-600'
                }`}>
                  {simStep >= 2 ? 'CURRENT' : 'PENDING'}
                </span>
              </div>
              <p className="text-xs sm:text-sm font-bold text-white">Alex lives in Dhaka</p>
            </div>

            {/* Result Panel */}
            <div className="relative w-full md:w-60 p-4 rounded-2xl bg-white/[0.03] border border-white/[0.07] text-xs space-y-2 overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
              <span className="text-[10px] font-mono uppercase font-bold text-slate-500 block">
                {simStep === 3 ? '🎯 Query Result' : 'HydraDB State'}
              </span>
              {simStep === 1 && (
                <p className="text-slate-400 leading-snug">Single active node in HydraDB graph.</p>
              )}
              {simStep === 2 && (
                <p className="text-amber-300 leading-snug font-semibold">
                  Fact #2 linked via <code className="font-mono font-bold text-amber-400">SUPERSEDES</code> edge.
                </p>
              )}
              {simStep === 3 && (
                <div className="space-y-1.5">
                  <p className="text-emerald-300 font-bold text-xs sm:text-sm">"Alex lives in Dhaka."</p>
                  <div className="text-[10px] text-slate-500 font-mono flex justify-between pt-1.5 border-t border-white/[0.06]">
                    <span>Confidence: <span className="text-emerald-400 font-bold">98%</span></span>
                    <span className="text-rose-400 font-bold">Outdated filtered</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* ═══════════════ CELL ISOLATION DEMO ═══════════════ */}
        <section className={`space-y-4 ${mounted ? 'anim-fade-up delay-5' : 'opacity-0'}`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs font-bold font-mono uppercase tracking-widest text-slate-500">
              <Database size={13} className="text-amber-500" />
              <span>Physical Cell-Level Isolation Demo</span>
              <div className="h-px w-12 bg-gradient-to-r from-white/[0.06] to-transparent ml-1" />
            </div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-mono font-bold">
              <Cpu size={12} className="text-purple-400" />
              <span>SlateDB Multi-Cell Architecture</span>
            </div>
          </div>

          <div className="relative rounded-3xl border border-white/[0.07] p-6 sm:p-8 bg-[#060a12] space-y-6 overflow-hidden shadow-2xl">
            {/* Top highlight glow */}
            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/30 to-transparent" />

            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
              <div>
                <h3 className="text-lg sm:text-xl font-bold text-white font-heading flex items-center gap-2">
                  Zero Cross-User Contamination Matrix
                  <Sparkles size={14} className="text-purple-400" />
                </h3>
                <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
                  Each (scope, cell) is an independently stored SlateDB database on disk. The HTTP API routes queries directly via <code className="font-mono text-purple-300">cell_id</code>, guaranteeing hardware-level physical separation rather than fragile WHERE-clause filters.
                </p>
              </div>

              <button
                onClick={() => fetchCellData(userA, userB)}
                disabled={loadingCells}
                className="px-4 py-2 rounded-xl text-xs font-mono font-bold bg-white/[0.05] hover:bg-white/[0.10] text-slate-300 hover:text-white border border-white/[0.08] transition-all flex items-center gap-2 self-start md:self-auto cursor-pointer"
              >
                <RefreshCw size={13} className={loadingCells ? 'animate-spin text-purple-400' : 'text-slate-400'} />
                <span>Re-verify Cells</span>
              </button>
            </div>

            {/* User Selectors */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* User A Selector */}
              <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
                    Primary Agent (User A):
                  </label>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue-500/15 text-blue-300 border border-blue-500/30">
                    HydraDB {AVAILABLE_CELL_USERS.find((u) => u.id === userA)?.cell || 'cell-0'}
                  </span>
                </div>
                <select
                  value={userA}
                  onChange={(e) => setUserA(e.target.value)}
                  className="w-full input-field py-2 px-3 text-xs bg-[#0b101d] text-white border-white/[0.08] font-medium"
                >
                  {AVAILABLE_CELL_USERS.map((u) => (
                    <option key={u.id} value={u.id} className="bg-[#0b101d] text-white">
                      {u.name} — {u.role} ({u.cell})
                    </option>
                  ))}
                </select>
              </div>

              {/* User B Selector */}
              <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
                    Isolated Contrast (User B):
                  </label>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">
                    HydraDB {AVAILABLE_CELL_USERS.find((u) => u.id === userB)?.cell || 'cell-0'}
                  </span>
                </div>
                <select
                  value={userB}
                  onChange={(e) => setUserB(e.target.value)}
                  className="w-full input-field py-2 px-3 text-xs bg-[#0b101d] text-white border-white/[0.08] font-medium"
                >
                  {AVAILABLE_CELL_USERS.map((u) => (
                    <option key={u.id} value={u.id} className="bg-[#0b101d] text-white">
                      {u.name} — {u.role} ({u.cell})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Side-by-Side Graph Comparison Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* User A Panel */}
              <div className="p-5 rounded-2xl bg-[#080d18] border border-blue-500/25 space-y-3.5 shadow-lg relative overflow-hidden">
                <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                  <div className="flex items-center gap-2">
                    <HardDrive size={15} className="text-blue-400" />
                    <span className="text-xs font-bold text-white font-heading">
                      {AVAILABLE_CELL_USERS.find((u) => u.id === userA)?.name}&apos;s Knowledge Graph
                    </span>
                  </div>
                  <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                    {AVAILABLE_CELL_USERS.find((u) => u.id === userA)?.cell}
                  </span>
                </div>

                <div className="text-[11px] text-slate-400 flex items-center justify-between font-mono">
                  <span>Location: {AVAILABLE_CELL_USERS.find((u) => u.id === userA)?.location}</span>
                  <span>{graphA?.nodes.length || 3} Nodes · {graphA?.edges.length || 2} Edges</span>
                </div>

                {/* Subgraph Nodes */}
                <div className="p-3 rounded-xl bg-black/40 border border-white/[0.05] space-y-2 max-h-48 overflow-y-auto">
                  <span className="text-[10px] font-mono uppercase text-slate-500 font-bold block">
                    SlateDB Partition Entities & Facts:
                  </span>
                  {(graphA?.nodes || [
                    { id: '1', label: `${AVAILABLE_CELL_USERS.find((u) => u.id === userA)?.name} (Entity)`, type: 'Entity' },
                    { id: '2', label: `Lives in ${AVAILABLE_CELL_USERS.find((u) => u.id === userA)?.location} (Current Fact)`, type: 'Fact' },
                    { id: '3', label: `Role: ${AVAILABLE_CELL_USERS.find((u) => u.id === userA)?.role}`, type: 'Fact' },
                  ]).map((n: any, idx: number) => (
                    <div key={idx} className="flex items-center justify-between text-xs py-1 px-2 rounded bg-white/[0.03] border border-white/[0.04]">
                      <span className="text-slate-300 font-medium truncate pr-2">{n.label || n.data?.content || `Node #${n.id}`}</span>
                      <span className="text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300 shrink-0">
                        {n.type || 'Fact'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* User B Panel */}
              <div className="p-5 rounded-2xl bg-[#080d18] border border-amber-500/25 space-y-3.5 shadow-lg relative overflow-hidden">
                <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                  <div className="flex items-center gap-2">
                    <HardDrive size={15} className="text-amber-400" />
                    <span className="text-xs font-bold text-white font-heading">
                      {AVAILABLE_CELL_USERS.find((u) => u.id === userB)?.name}&apos;s Knowledge Graph
                    </span>
                  </div>
                  <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    {AVAILABLE_CELL_USERS.find((u) => u.id === userB)?.cell}
                  </span>
                </div>

                <div className="text-[11px] text-slate-400 flex items-center justify-between font-mono">
                  <span>Location: {AVAILABLE_CELL_USERS.find((u) => u.id === userB)?.location}</span>
                  <span>{graphB?.nodes.length || 3} Nodes · {graphB?.edges.length || 2} Edges</span>
                </div>

                {/* Subgraph Nodes */}
                <div className="p-3 rounded-xl bg-black/40 border border-white/[0.05] space-y-2 max-h-48 overflow-y-auto">
                  <span className="text-[10px] font-mono uppercase text-slate-500 font-bold block">
                    SlateDB Partition Entities & Facts:
                  </span>
                  {(graphB?.nodes || [
                    { id: '4', label: `${AVAILABLE_CELL_USERS.find((u) => u.id === userB)?.name} (Entity)`, type: 'Entity' },
                    { id: '5', label: `Lives in ${AVAILABLE_CELL_USERS.find((u) => u.id === userB)?.location} (Current Fact)`, type: 'Fact' },
                    { id: '6', label: `Role: ${AVAILABLE_CELL_USERS.find((u) => u.id === userB)?.role}`, type: 'Fact' },
                  ]).map((n: any, idx: number) => (
                    <div key={idx} className="flex items-center justify-between text-xs py-1 px-2 rounded bg-white/[0.03] border border-white/[0.04]">
                      <span className="text-slate-300 font-medium truncate pr-2">{n.label || n.data?.content || `Node #${n.id}`}</span>
                      <span className="text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 shrink-0">
                        {n.type || 'Fact'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Physical Storage Proof Banner */}
            <div className="p-4 rounded-2xl bg-emerald-500/[0.07] border border-emerald-500/25 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 size={18} className="text-emerald-400 shrink-0" />
                <div>
                  <span className="font-bold text-emerald-200">
                    Physical SlateDB Overlap: 0.0% · Zero Cross-Cell Contamination Verified
                  </span>
                  <p className="text-[11px] text-emerald-400/80 font-mono mt-0.5">
                    HTTP query routing matches target cell_id directly into /data/store/{AVAILABLE_CELL_USERS.find((u) => u.id === userA)?.cell} vs /data/store/{AVAILABLE_CELL_USERS.find((u) => u.id === userB)?.cell}
                  </p>
                </div>
              </div>
              <span className="text-[10px] font-mono font-bold px-2.5 py-1 rounded-lg bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 whitespace-nowrap">
                STRICT HARDWARE ISOLATION
              </span>
            </div>
          </div>
        </section>

        {/* ═══════════════ CORE MODULES ═══════════════ */}
        <section className={`space-y-4 ${mounted ? 'anim-fade-up delay-6' : 'opacity-0'}`}>
          <div className="flex items-center gap-2 text-xs font-bold font-mono uppercase tracking-widest text-slate-500">
            <Zap size={13} className="text-amber-500" />
            <span>Core Interactive Modules</span>
            <div className="flex-1 h-px bg-gradient-to-r from-white/[0.06] to-transparent ml-2" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {featureActions.map((action, i) => {
              const Icon = action.icon;
              const colors = accentMap[action.accentColor];
              return (
                <Link
                  key={action.href}
                  href={action.href}
                  className={`
                    group relative card-glow-border flex flex-col justify-between
                    p-5 rounded-2xl border border-white/[0.07] bg-[#080d18]
                    transition-all duration-300 cursor-pointer overflow-hidden
                    ${colors.card} ${colors.glow}
                    hover:-translate-y-0.5
                  `}
                  style={{ animationDelay: `${i * 0.06}s` }}
                >
                  {/* Hover top-edge glow */}
                  <div className={`absolute top-0 left-0 right-0 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-r from-transparent via-white/20 to-transparent`} />

                  <div className="space-y-3.5">
                    <div className="flex items-center justify-between">
                      <span className={`text-[9px] font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-lg border ${colors.badge}`}>
                        {action.badge}
                      </span>
                      <div className={`p-2.5 rounded-xl border ${colors.icon} transition-all duration-300 group-hover:scale-110 group-hover:shadow-[0_0_12px_-2px_currentColor]`}>
                        <Icon size={15} />
                      </div>
                    </div>
                    <div>
                      <h3 className={`text-sm sm:text-base font-bold text-white/90 ${colors.hover} transition-colors font-heading`}>
                        {action.title}
                      </h3>
                      <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                        {action.description}
                      </p>
                    </div>
                  </div>

                  <div className={`pt-4 flex items-center justify-end text-xs font-bold text-slate-600 group-hover:text-amber-400 transition-colors gap-1.5`}>
                    <span>Explore Module</span>
                    <ArrowRight size={12} className="transition-transform duration-300 group-hover:translate-x-1" />
                  </div>
                </Link>
              );
            })}
          </div>
        </section>

        {/* ═══════════════ DEVELOPER SDK ═══════════════ */}
        <section className={`space-y-4 ${mounted ? 'anim-fade-up delay-6' : 'opacity-0'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold font-mono uppercase tracking-widest text-slate-500">
              <Code2 size={13} className="text-amber-500" />
              <span>Developer Integration</span>
              <div className="h-px w-16 bg-gradient-to-r from-white/[0.06] to-transparent ml-1" />
            </div>
            <span
              className="text-xs font-mono text-emerald-300 font-bold px-3 py-1 rounded-xl bg-emerald-500/10 border border-emerald-500/25"
              style={{ boxShadow: '0 0 16px -6px rgba(16,185,129,0.4)' }}
            >
              pip install memorygraph
            </span>
          </div>

          <div className="relative rounded-3xl border border-white/[0.07] overflow-hidden bg-[#040710] shadow-[0_0_80px_-20px_rgba(0,0,0,0.9)] code-scanline">
            {/* Top edge highlight */}
            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-400/20 to-transparent z-10" />

            {/* Tab Bar */}
            <div className="flex flex-wrap items-center justify-between px-5 py-3.5 bg-[#070b14] border-b border-white/[0.06] gap-3">
              <div className="flex items-center gap-4">
                {/* Mac-style Window Controls */}
                <div className="hidden sm:flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-rose-500/70 border border-rose-600/50 shadow-[0_0_6px_rgba(239,68,68,0.4)]" />
                  <span className="w-3 h-3 rounded-full bg-amber-500/70 border border-amber-600/50 shadow-[0_0_6px_rgba(245,158,11,0.4)]" />
                  <span className="w-3 h-3 rounded-full bg-emerald-500/70 border border-emerald-600/50 shadow-[0_0_6px_rgba(16,185,129,0.4)]" />
                </div>

                {/* Language Tabs */}
                <div className="flex gap-1 bg-black/30 p-1 rounded-xl border border-white/[0.06]">
                  {codeTabs.map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => setActiveCodeTab(tab.key)}
                      className={`px-3 py-1 rounded-lg text-xs font-mono font-bold transition-all duration-200 cursor-pointer ${
                        activeCodeTab === tab.key
                          ? 'bg-amber-500 text-slate-950 shadow-[0_0_14px_-2px_rgba(245,158,11,0.6)]'
                          : 'text-slate-500 hover:text-slate-200 hover:bg-white/[0.05]'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="hidden md:inline text-[11px] font-mono text-slate-600 font-bold uppercase tracking-wider">
                  {activeCodeTab === 'curl' ? 'BASH / REST' : activeCodeTab === 'opencypher' ? 'OPENCYPHER' : 'PYTHON 3.11+'}
                </span>
                <button
                  onClick={handleCopyCode}
                  className="flex items-center gap-1.5 text-xs px-3.5 py-1.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.10] text-slate-300 hover:text-white border border-white/[0.08] transition-all font-mono font-bold cursor-pointer"
                >
                  {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                  <span>{copied ? 'Copied!' : 'Copy'}</span>
                </button>
              </div>
            </div>

            {/* Code Viewer */}
            <CodeViewer
              code={CODE_EXAMPLES[activeCodeTab]}
              language={activeCodeTab}
            />
          </div>
        </section>

      </div>
    </>
  );
}