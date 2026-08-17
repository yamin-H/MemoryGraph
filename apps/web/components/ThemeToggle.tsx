'use client';

import { useTheme } from './ThemeProvider';
import { Sun, Moon } from 'lucide-react';
import { useEffect, useState } from 'react';

interface ThemeToggleProps {
  showLabel?: boolean;
  className?: string;
}

export function ThemeToggle({ showLabel = false, className = '' }: ThemeToggleProps) {
  const { resolvedTheme, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className={`p-2.5 rounded-xl border border-transparent w-10 h-10 ${className}`} />
    );
  }

  const isDark = resolvedTheme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`
        relative group flex items-center justify-center gap-2 p-2.5 rounded-xl
        border transition-all duration-300 ease-out cursor-pointer
        bg-white dark:bg-slate-800/90
        hover:bg-slate-100 dark:hover:bg-slate-700
        border-slate-200 dark:border-white/[0.1]
        text-slate-700 dark:text-slate-200
        hover:text-amber-600 dark:hover:text-amber-400
        shadow-sm hover:shadow-md
        ${className}
      `}
      title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
      aria-label="Toggle theme"
    >
      <div className="relative w-4 h-4 flex items-center justify-center">
        <Sun
          size={17}
          className={`
            absolute transition-all duration-300 transform
            text-amber-500
            ${isDark ? 'rotate-90 scale-0 opacity-0' : 'rotate-0 scale-100 opacity-100'}
          `}
        />
        <Moon
          size={17}
          className={`
            absolute transition-all duration-300 transform
            text-amber-400
            ${isDark ? 'rotate-0 scale-100 opacity-100' : '-rotate-90 scale-0 opacity-0'}
          `}
        />
      </div>

      {showLabel && (
        <span className="text-xs font-bold select-none capitalize">
          {isDark ? 'Dark Mode' : 'Light Mode'}
        </span>
      )}
    </button>
  );
}
