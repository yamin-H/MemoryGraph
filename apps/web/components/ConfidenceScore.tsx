'use client';

interface ConfidenceScoreProps {
  score: number;
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

export function ConfidenceScore({ score, showLabel = true, size = 'md' }: ConfidenceScoreProps) {
  const percentage = Math.round(score * 100);
  
  let colorStyle = {
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/30',
    text: 'text-rose-400',
    dot: 'bg-rose-400',
    label: 'Low',
  };

  if (score >= 0.8) {
    colorStyle = {
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/30',
      text: 'text-emerald-400',
      dot: 'bg-emerald-400',
      label: 'High',
    };
  } else if (score >= 0.5) {
    colorStyle = {
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/30',
      text: 'text-amber-400',
      dot: 'bg-amber-400',
      label: 'Medium',
    };
  }

  return (
    <div className="inline-flex items-center gap-2">
      <span
        className={`inline-flex items-center gap-1.5 font-semibold font-mono rounded-full border ${colorStyle.bg} ${colorStyle.border} ${colorStyle.text} ${
          size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1'
        }`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${colorStyle.dot} animate-pulse`} />
        {percentage}%
      </span>
      {showLabel && (
        <span className="text-[11px] text-slate-400 font-medium">
          {colorStyle.label} confidence
        </span>
      )}
    </div>
  );
}
