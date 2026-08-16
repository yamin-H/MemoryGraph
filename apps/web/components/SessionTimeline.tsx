'use client';

import { formatDistanceToNow } from 'date-fns';
import { Calendar, FileText, Sparkles, Clock } from 'lucide-react';
import Link from 'next/link';

interface SessionTimelineProps {
  sessions?: Array<{
    id: string;
    date: string;
    summary?: string;
    factCount: number;
  }>;
}

export function SessionTimeline({ sessions = [] }: SessionTimelineProps) {
  if (sessions.length === 0) {
    return (
      <div className="text-center py-10 text-slate-500 text-xs">
        <Clock size={20} className="mx-auto mb-2 opacity-50" />
        No session history recorded yet
      </div>
    );
  }

  return (
    <div className="space-y-3 relative before:absolute before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-white/[0.08]">
      {sessions.map((session) => {
        let formattedDate = 'Recently';
        try {
          const d = new Date(session.date);
          if (!isNaN(d.getTime())) {
            formattedDate = formatDistanceToNow(d, { addSuffix: true });
          }
        } catch {
          formattedDate = session.date;
        }

        return (
          <div key={session.id} className="relative flex items-start gap-4 pl-1">
            {/* Node marker */}
            <div className="w-6 h-6 rounded-full bg-slate-900 border-2 border-amber-400 flex items-center justify-center flex-shrink-0 z-10 shadow-md mt-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            </div>

            {/* Card */}
            <div className="flex-1 glass-card p-3.5 space-y-1.5 hover:border-amber-500/30 transition-all">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 text-xs text-slate-400">
                  <Calendar size={12} />
                  <span>{formattedDate}</span>
                  <span className="text-slate-600">•</span>
                  <Link
                    href={`/graph`}
                    className="font-mono text-amber-400 hover:underline text-[11px]"
                  >
                    {session.id}
                  </Link>
                </div>
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                  <Sparkles size={10} />
                  {session.factCount} facts
                </span>
              </div>

              {session.summary && (
                <div className="flex items-start gap-1.5 pt-0.5 text-xs text-slate-300 leading-relaxed">
                  <FileText size={12} className="text-slate-500 mt-0.5 flex-shrink-0" />
                  <p className="line-clamp-2">{session.summary}</p>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
