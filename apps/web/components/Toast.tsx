'use client';

import { useState } from 'react';
import { useToasts, removeToast } from '@/lib/hooks';
import { X, CheckCircle2, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import type { Toast as ToastType } from '@/lib/types';

const iconMap = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
  warning: AlertTriangle,
};

const colorMap = {
  success: {
    bg: 'bg-emerald-950/90',
    border: 'border-emerald-500/30',
    icon: 'text-emerald-400',
    progress: 'bg-emerald-400',
  },
  error: {
    bg: 'bg-rose-950/90',
    border: 'border-rose-500/30',
    icon: 'text-rose-400',
    progress: 'bg-rose-400',
  },
  info: {
    bg: 'bg-blue-950/90',
    border: 'border-blue-500/30',
    icon: 'text-blue-400',
    progress: 'bg-blue-400',
  },
  warning: {
    bg: 'bg-amber-950/90',
    border: 'border-amber-500/30',
    icon: 'text-amber-400',
    progress: 'bg-amber-400',
  },
};

function ToastItem({ toast }: { toast: ToastType }) {
  const [exiting, setExiting] = useState(false);
  const Icon = iconMap[toast.type];
  const colors = colorMap[toast.type];

  const handleDismiss = () => {
    setExiting(true);
    setTimeout(() => removeToast(toast.id), 200);
  };

  return (
    <div
      className={`relative overflow-hidden transition-all duration-200 ${
        exiting ? 'opacity-0 translate-x-4 scale-95' : 'opacity-100 translate-x-0 scale-100 animate-[slideInRight_0.25s_ease-out]'
      } ${colors.bg} ${colors.border} border rounded-xl p-4 shadow-2xl max-w-sm w-full backdrop-blur-xl`}
    >
      <div className="flex items-start gap-3">
        <Icon size={18} className={`${colors.icon} mt-0.5 flex-shrink-0`} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-slate-100">{toast.title}</p>
          {toast.message && (
            <p className="text-[11px] text-slate-300 mt-0.5 leading-normal">{toast.message}</p>
          )}
        </div>
        <button
          onClick={handleDismiss}
          className="text-slate-400 hover:text-slate-200 transition-colors p-0.5"
        >
          <X size={13} />
        </button>
      </div>
      {toast.duration && toast.duration > 0 && (
        <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-white/10 overflow-hidden">
          <div
            className={`h-full ${colors.progress}`}
            style={{
              animation: `shimmer ${toast.duration}ms linear forwards`,
              width: '100%',
            }}
          />
        </div>
      )}
    </div>
  );
}

export function ToastContainer() {
  const { toasts } = useToasts();
  if (!toasts || toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col-reverse gap-2.5 pointer-events-none">
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <ToastItem toast={toast} />
        </div>
      ))}
    </div>
  );
}
