'use client';

import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center animate-fade-in">
      <div className="w-16 h-16 rounded-3xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-4 shadow-md shadow-amber-500/5">
        <Icon size={28} className="text-amber-600 dark:text-amber-400" />
      </div>
      <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 mb-1.5 font-heading">{title}</h3>
      <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 max-w-sm mb-6 leading-relaxed font-medium">{description}</p>
      {action && (
        <button onClick={action.onClick} className="btn-primary text-xs px-5 py-2.5 shadow-md">
          {action.label}
        </button>
      )}
    </div>
  );
}
