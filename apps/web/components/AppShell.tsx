'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  MessageSquare,
  Network,
  BarChart3,
  Upload,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  Database,
  ExternalLink,
  Swords,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { useHealth } from '@/lib/hooks';
import { ToastContainer } from './Toast';
import { ThemeToggle } from './ThemeToggle';

const navItems = [
  { href: '/', label: 'Overview', icon: LayoutDashboard },
  { href: '/arena', label: 'Battle Arena', icon: Swords, badge: 'VS', badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20' },
  { href: '/abstention', label: 'Abstention', icon: ShieldCheck, badge: 'TRUTH', badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20' },
  { href: '/chat', label: 'Agent Chat', icon: MessageSquare },
  { href: '/graph', label: 'Graph Explorer', icon: Network },
  { href: '/benchmark', label: 'Benchmarks', icon: BarChart3 },
  { href: '/ingest', label: 'Ingestion', icon: Upload },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { health } = useHealth();

  const isHealthy = health?.status === 'ok';

  return (
    <div className="flex h-screen overflow-hidden bg-transparent text-slate-900 dark:text-slate-100 antialiased font-sans transition-colors duration-200">
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/50 dark:bg-black/75 z-40 lg:hidden backdrop-blur-sm animate-fade-in"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:relative inset-y-0 left-0 z-50
          flex flex-col
          bg-white/80 dark:bg-[#0b101c]/90 
          border-r border-slate-200/90 dark:border-white/[0.06] 
          backdrop-blur-2xl shadow-lg lg:shadow-none
          transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]
          ${collapsed ? 'w-[72px]' : 'w-64'}
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Brand */}
        <div className={`flex items-center h-16 px-4 border-b border-slate-200 dark:border-white/[0.06] flex-shrink-0 ${collapsed ? 'justify-center' : 'justify-between'}`}>
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-400 via-amber-500 to-amber-600 flex items-center justify-center flex-shrink-0 shadow-md shadow-amber-500/25 group-hover:scale-105 transition-transform duration-300">
              <Network size={18} className="text-slate-950 stroke-[2.5]" />
            </div>
            {!collapsed && (
              <div>
                <span className="text-sm font-black tracking-tight text-slate-900 dark:text-white font-heading flex items-center gap-1.5">
                  MemoryGraph
                  <Sparkles size={11} className="text-amber-500 dark:text-amber-400 inline" />
                </span>
                <p className="text-[9px] font-mono uppercase tracking-[0.15em] text-amber-600 dark:text-amber-400/90 font-bold">
                  HydraDB Layer
                </p>
              </div>
            )}
          </Link>

          <button
            onClick={() => setMobileOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/[0.05] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Nav Links */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          <div className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 dark:text-slate-500 px-3 py-2 font-mono">
            {!collapsed ? 'Core Modules' : '···'}
          </div>

          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`
                  group flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold
                  transition-all duration-200 relative
                  ${
                    isActive
                      ? 'bg-amber-500/10 dark:bg-white/[0.08] text-amber-700 dark:text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100/80 dark:hover:bg-white/[0.04]'
                  }
                  ${collapsed ? 'justify-center px-0' : ''}
                `}
                title={collapsed ? item.label : undefined}
              >
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-amber-500 rounded-r-full" />
                )}
                <Icon
                  size={18}
                  className={`flex-shrink-0 transition-all duration-200 ${
                    isActive ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400 dark:text-slate-500 group-hover:text-slate-700 dark:group-hover:text-slate-300'
                  }`}
                />
                {!collapsed && (
                  <div className="flex items-center justify-between flex-1 min-w-0">
                    <span className="truncate">{item.label}</span>
                    {item.badge && (
                      <span className={`text-[8px] font-black uppercase px-1.5 py-0.5 rounded-md border ${item.badgeColor}`}>
                        {item.badge}
                      </span>
                    )}
                  </div>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className={`p-3 border-t border-slate-200 dark:border-white/[0.06] flex-shrink-0 space-y-2 ${collapsed ? 'flex flex-col items-center' : ''}`}>
          {!collapsed ? (
            <div className="p-3 rounded-xl bg-slate-100/70 dark:bg-white/[0.02] border border-slate-200 dark:border-white/[0.05] space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400 flex items-center gap-1.5 font-mono">
                  <Database size={11} className="text-amber-500 dark:text-amber-400" />
                  HydraDB Cluster
                </span>
                <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50' : 'bg-amber-500'}`} />
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-400 font-mono flex items-center justify-between">
                <span>{isHealthy ? 'Connected' : 'Connecting...'}</span>
                <span className="text-[9px] text-slate-400 dark:text-slate-500">Track 03</span>
              </p>
            </div>
          ) : (
            <div className="p-2">
              <span className={`w-2.5 h-2.5 rounded-full block mx-auto ${isHealthy ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50' : 'bg-amber-500'}`} title="HydraDB Status" />
            </div>
          )}

          <div className="flex items-center justify-between gap-1 pt-1">
            <ThemeToggle showLabel={!collapsed} className={collapsed ? 'w-full justify-center' : 'flex-1'} />

            <button
              onClick={() => setCollapsed(!collapsed)}
              className="hidden lg:flex items-center justify-center p-2 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/[0.04] transition-colors"
              title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
            >
              {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative z-10">
        {/* Top Bar */}
        <header className="flex items-center justify-between h-16 px-6 border-b border-slate-200/90 dark:border-white/[0.06] bg-white/75 dark:bg-[#070b14]/80 backdrop-blur-2xl flex-shrink-0 z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 rounded-xl text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/[0.04] transition-colors"
            >
              <Menu size={20} />
            </button>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 dark:text-slate-500 font-mono">HACK HYDRA · TRACK 03</span>
              <span className="text-slate-300 dark:text-slate-700">/</span>
              <span className="text-xs font-bold text-slate-800 dark:text-slate-200 font-heading">
                {navItems.find((n) => n.href === pathname)?.label || 'Overview'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/arena"
              className="inline-flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-300 font-bold px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 transition-all duration-300 shadow-sm"
            >
              <Swords size={13} className="text-amber-500 dark:text-amber-400" />
              <span>Battle Arena</span>
            </Link>

            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="hidden md:inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-white/[0.08] hover:border-slate-300 dark:hover:border-white/[0.15] bg-white/50 dark:bg-white/[0.02] transition-all duration-300"
            >
              <span>API Docs</span>
              <ExternalLink size={11} />
            </a>

            <ThemeToggle />

            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100/80 dark:bg-white/[0.03] border border-slate-200 dark:border-white/[0.06]">
              <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-500' : 'bg-amber-500'} animate-pulse`} />
              <span className="text-[11px] font-mono text-slate-700 dark:text-slate-300 font-bold">
                {isHealthy ? 'READY' : 'STANDBY'}
              </span>
            </div>
          </div>
        </header>

        {/* Page Content Viewport */}
        <main
          className={`flex-1 min-h-0 ${
            pathname === '/graph' || pathname === '/chat'
              ? 'overflow-hidden'
              : 'overflow-y-auto'
          }`}
        >
          {children}
        </main>
      </div>

      <ToastContainer />
    </div>
  );
}
