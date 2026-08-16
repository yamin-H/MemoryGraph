'use client';

import { useState, useRef, useEffect, useCallback, KeyboardEvent } from 'react';
import { api } from '@/lib/api';
import { Message, QueryResponse } from '@/lib/types';
import { ConfidenceScore } from './ConfidenceScore';
import { Send, Loader2, Bot, User, Sparkles, AlertTriangle, Clock, Terminal, ChevronRight } from 'lucide-react';
import { addToast } from '@/lib/hooks';

interface ChatInterfaceProps {
  onAnswerChange?: (answer: QueryResponse | null) => void;
}

const suggestedQueries = [
  'What facts do you remember about Alex?',
  'Has any pet or work information changed over time?',
  'What were the main topics discussed across sessions?',
  'Can you synthesize what is known about the user profile?',
];

export function ChatInterface({ onAnswerChange }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeReasoningIdx, setActiveReasoningIdx] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
    }
  }, [input]);

  const handleSendMessage = useCallback(
    async (textToSend?: string) => {
      const query = (textToSend ?? input).trim();
      if (!query || loading) return;

      const userMessage: Message = {
        role: 'user',
        content: query,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setInput('');
      setLoading(true);

      try {
        const response = await api.queryMemory(query, 'user');

        const assistantMessage: Message = {
          role: 'assistant',
          content: response.answer,
          confidence: response.confidence,
          abstained: response.abstained,
          abstentionReason: response.abstention_reason,
          sourceSessions: response.source_sessions,
          supersededFacts: response.superseded_facts,
          reasoning: response.reasoning,
          queryTimeMs: response.query_time_ms,
          groqTokensUsed: response.groq_tokens_used,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
        onAnswerChange?.(response);
      } catch (err: any) {
        addToast('error', 'Query Failed', 'Backend query failed. Please verify API & HydraDB status.');
        const errorMessage: Message = {
          role: 'assistant',
          content: 'Unable to query the MemoryGraph layer. Please make sure the backend services are running.',
          confidence: 0,
          abstained: true,
          abstentionReason: 'Network/Service Connection Error',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setLoading(false);
      }
    },
    [input, loading, onAnswerChange]
  );

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950/40">
      {/* Messages stream */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center min-h-[380px] text-center px-4 animate-[fadeIn_0.3s_ease-out]">
            <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-4 shadow-lg shadow-amber-500/5">
              <Bot size={30} className="text-amber-400" />
            </div>
            <h2 className="text-lg font-bold text-slate-100 mb-1">MemoryGraph Agent Chat</h2>
            <p className="text-xs text-slate-400 max-w-md mb-8 leading-relaxed">
              Temporal knowledge graph memory. Query across all sessions with automated confidence estimation and fact supersedence.
            </p>

            <div className="w-full max-w-lg space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Suggested queries</p>
              {suggestedQueries.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(q)}
                  className="w-full text-left p-3 rounded-xl bg-slate-900/60 hover:bg-slate-800/80 border border-white/[0.06] hover:border-amber-500/30 text-xs text-slate-300 hover:text-amber-300 transition-all flex items-center justify-between group"
                >
                  <span className="flex items-center gap-2">
                    <Sparkles size={13} className="text-amber-400/70 group-hover:text-amber-400" />
                    {q}
                  </span>
                  <ChevronRight size={13} className="text-slate-600 group-hover:text-amber-400 group-hover:translate-x-0.5 transition-all" />
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message, idx) => {
          const isUser = message.role === 'user';
          return (
            <div
              key={idx}
              className={`flex gap-3.5 ${isUser ? 'justify-end' : 'justify-start'} animate-[fadeInUp_0.25s_ease-out]`}
            >
              {!isUser && (
                <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center flex-shrink-0 text-amber-400 mt-1">
                  <Bot size={16} />
                </div>
              )}

              <div
                className={`max-w-[85%] sm:max-w-xl rounded-2xl p-4 space-y-3 ${
                  isUser
                    ? 'bg-amber-500 text-slate-950 rounded-tr-sm font-medium shadow-md shadow-amber-500/10'
                    : 'glass-card text-slate-100 rounded-tl-sm'
                }`}
              >
                <div className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap">
                  {message.content}
                </div>

                {!isUser && (
                  <div className="pt-2 border-t border-white/5 space-y-2.5">
                    {/* Confidence & latency header */}
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      {message.confidence !== undefined && (
                        <ConfidenceScore score={message.confidence} />
                      )}
                      {message.queryTimeMs !== undefined && (
                        <span className="text-[11px] text-slate-500 font-mono flex items-center gap-1">
                          <Clock size={11} />
                          {message.queryTimeMs}ms
                        </span>
                      )}
                    </div>

                    {/* Abstention notice */}
                    {message.abstained && (
                      <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-start gap-2 text-xs text-amber-300">
                        <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
                        <div>
                          <span className="font-semibold">Abstained:</span> {message.abstentionReason || 'Insufficient memory confidence'}
                        </div>
                      </div>
                    )}

                    {/* Source sessions */}
                    {message.sourceSessions && message.sourceSessions.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="text-[10px] uppercase font-semibold text-slate-500">Sources:</span>
                        {message.sourceSessions.map((sess, i) => (
                          <span
                            key={i}
                            className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-white/[0.04] border border-white/[0.08] text-slate-300"
                          >
                            {sess}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Reasoning expandable drawer */}
                    {message.reasoning && (
                      <div className="pt-1">
                        <button
                          onClick={() => setActiveReasoningIdx(activeReasoningIdx === idx ? null : idx)}
                          className="text-[11px] text-amber-400/80 hover:text-amber-400 flex items-center gap-1 font-medium transition-colors"
                        >
                          <Terminal size={12} />
                          {activeReasoningIdx === idx ? 'Hide Graph Reasoning' : 'View Graph Reasoning'}
                        </button>
                        {activeReasoningIdx === idx && (
                          <div className="mt-2 p-3 rounded-lg bg-black/40 border border-white/[0.08] text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-wrap animate-[fadeIn_0.2s_ease-out]">
                            {message.reasoning}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {isUser && (
                <div className="w-8 h-8 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center flex-shrink-0 text-amber-400 mt-1">
                  <User size={16} />
                </div>
              )}
            </div>
          );
        })}

        {/* Loading state indicator */}
        {loading && (
          <div className="flex gap-3.5 justify-start animate-[fadeIn_0.2s_ease-out]">
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center flex-shrink-0 text-amber-400">
              <Bot size={16} />
            </div>
            <div className="glass-card p-4 rounded-2xl rounded-tl-sm flex items-center gap-3">
              <Loader2 size={16} className="text-amber-400 animate-spin" />
              <span className="text-xs text-slate-400">Traversing HydraDB & computing temporal facts...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input container */}
      <div className="p-4 border-t border-white/[0.08] bg-slate-900/60 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto flex gap-2.5 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about long-term memories, facts, or entities... (Enter to send, Shift+Enter for newline)"
              rows={1}
              disabled={loading}
              className="input-field min-h-[44px] max-h-[140px] resize-none py-2.5 pr-10 text-xs sm:text-sm"
            />
          </div>
          <button
            onClick={() => handleSendMessage()}
            disabled={loading || !input.trim()}
            className="btn-primary h-[44px] px-4 flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </div>
  );
}
