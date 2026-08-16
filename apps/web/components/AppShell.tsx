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
} from 'lucide-react';
import { useHealth } from '@/lib/hooks';
import { ToastContainer } from './Toast';

const navItems = [
  { href: '/', label: 'Overview', icon: LayoutDashboard },
  { href: '/chat', label: 'Agent Chat', icon: MessageSquare },
  { href: '/graph', label: 'Graph Explorer', icon: Network },
  { href: '/benchmark', label: 'Benchmarks', icon: BarChart3 },
  { href: '/ingest', label: 'Session Ingestion', icon: Upload },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { health } = useHealth();

  const isHealthy = health?.status === 'ok';

  return (
    <div className="flex h-screen overflow-hidden bg-[#080b11] text-slate-100 antialiased font-sans">
      {/* Mobile Drawer Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/75 z-40 lg:hidden backdrop-blur-sm animate-[fadeIn_0.2s_ease-out]"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar Navigation */}
      <aside
        className={`
          fixed lg:relative inset-y-0 left-0 z-50
          flex flex-col
          bg-[#0d121c] border-r border-white/[0.08]
          transition-all duration-300 ease-in-out
          ${collapsed ? 'w-[72px]' : 'w-64'}
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Brand Header */}
        <div className={`flex items-center h-16 px-4 border-b border-white/[0.08] flex-shrink-0 ${collapsed ? 'justify-center' : 'justify-between'}`}>
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-amber-500/20 group-hover:scale-105 transition-transform">
              <Network size={20} className="text-slate-950 stroke-[2.5]" />
            </div>
            {!collapsed && (
              <div>
                <span className="text-sm font-black tracking-tight text-white flex items-center gap-1.5">
                  MemoryGraph
                </span>
                <p className="text-[10px] font-mono uppercase tracking-wider text-amber-400/90 font-semibold">
                  HydraDB Layer
                </p>
              </div>
            )}
          </Link>

          {/* Mobile close button */}
          <button
            onClick={() => setMobileOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation links */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-1.5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-3 py-1">
            {!collapsed ? 'Navigation' : '•••'}
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
                  group flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold
                  transition-all duration-200 relative
                  ${
                    isActive
                      ? 'bg-amber-500/10 text-amber-300 border border-amber-500/25 shadow-sm'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-white/[0.04]'
                  }
                  ${collapsed ? 'justify-center px-0' : ''}
                `}
                title={collapsed ? item.label : undefined}
              >
                <Icon
                  size={18}
                  className={`flex-shrink-0 transition-transform group-hover:scale-110 ${
                    isActive ? 'text-amber-400' : 'text-slate-400 group-hover:text-slate-200'
                  }`}
                />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Status / Quick info footer */}
        <div className={`p-3 border-t border-white/[0.08] bg-black/20 flex-shrink-0 ${collapsed ? 'flex flex-col items-center' : ''}`}>
          {!collapsed ? (
            <div className="p-3 rounded-xl bg-slate-900/80 border border-white/[0.06] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Database size={11} className="text-amber-400" />
                  HydraDB Node
                </span>
                <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              </div>
              <p className="text-[11px] text-slate-400 font-mono">
                {isHealthy ? 'Connected & Synced' : 'Connecting to cluster...'}
              </p>
            </div>
          ) : (
            <div className="p-2">
              <span className={`w-2.5 h-2.5 rounded-full block ${isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} title="HydraDB Status" />
            </div>
          )}

          {/* Desktop collapse toggle */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden lg:flex items-center justify-center w-full mt-2 py-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-white/5 transition-colors"
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>
      </aside>

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Navbar */}
        <header className="flex items-center justify-between h-16 px-6 border-b border-white/[0.08] bg-[#0d121c]/70 backdrop-blur-xl flex-shrink-0 z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5"
            >
              <Menu size={20} />
            </button>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-widest text-slate-500 font-mono">WORKSPACE</span>
              <span className="text-slate-600">/</span>
              <span className="text-xs font-semibold text-slate-200">
                {navItems.find((n) => n.href === pathname)?.label || 'Overview'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-amber-400 px-3 py-1.5 rounded-lg border border-white/[0.08] hover:border-amber-500/30 transition-colors"
            >
              <span>Swagger API Docs</span>
              <ExternalLink size={12} />
            </a>

            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.08]">
              <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400' : 'bg-rose-400'}`} />
              <span className="text-[11px] font-mono text-slate-300 font-medium">
                {isHealthy ? 'ONLINE' : 'DEGRADED'}
              </span>
            </div>
          </div>
        </header>

        {/* Active Page Viewport */}
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

      {/* Global Toast Overlay */}
      <ToastContainer />
    </div>
  );
}
