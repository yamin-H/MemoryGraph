'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { addToast } from '@/lib/hooks';
import { Upload, Plus, Trash2, Loader2, Sparkles, FileJson, CheckCircle2, MessageSquare, Bot, User } from 'lucide-react';

interface MessageRow {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

const sampleTemplates = [
  {
    name: 'Session 1: Initial Intro',
    session_id: 'alex-session-1',
    user_id: 'alex',
    started_at: '2024-01-10T10:00:00Z',
    messages: [
      { role: 'user', content: 'Hi! My name is Alex. I am a software engineer working at TechCorp in San Francisco.' },
      { role: 'assistant', content: 'Nice to meet you Alex! How is San Francisco treating you?' },
      { role: 'user', content: 'I live in a small apartment with my golden retriever puppy named Mochi.' },
      { role: 'assistant', content: 'Golden retrievers are wonderful pets! Mochi is an adorable name.' },
    ],
  },
  {
    name: 'Session 2: Fact Update (Relocation & Pet)',
    session_id: 'alex-session-2',
    user_id: 'alex',
    started_at: '2024-01-20T14:30:00Z',
    messages: [
      { role: 'user', content: 'Quick update: I actually moved from San Francisco to Seattle last weekend for a new job at CloudScale.' },
      { role: 'assistant', content: 'Congratulations on the new job at CloudScale and the move to Seattle!' },
      { role: 'user', content: 'Also Mochi now has a cat sibling named Pixel who is 1 year old.' },
      { role: 'assistant', content: 'How are Mochi and Pixel getting along in Seattle?' },
    ],
  },
  {
    name: 'Session 3: Project Work',
    session_id: 'alex-session-3',
    user_id: 'alex',
    started_at: '2024-02-05T09:15:00Z',
    messages: [
      { role: 'user', content: 'I am currently designing a graph database architecture using HydraDB.' },
      { role: 'assistant', content: 'HydraDB offers great performance for graph-native agent workflows!' },
    ],
  },
];

export function IngestPage() {
  const [sessionId, setSessionId] = useState('');
  const [userId, setUserId] = useState('');
  const [startedAt, setStartedAt] = useState('');
  const [messages, setMessages] = useState<MessageRow[]>([
    { id: '1', role: 'user', content: '' },
    { id: '2', role: 'assistant', content: '' },
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [lastIngestResult, setLastIngestResult] = useState<any>(null);

  const handleLoadSample = (tpl: (typeof sampleTemplates)[0]) => {
    setSessionId(tpl.session_id);
    setUserId(tpl.user_id);
    setStartedAt(tpl.started_at);
    setMessages(
      tpl.messages.map((m, i) => ({
        id: String(i + 1),
        role: m.role as 'user' | 'assistant',
        content: m.content,
      }))
    );
    addToast('info', 'Template Loaded', `Loaded "${tpl.name}" into form.`);
  };

  const addMessage = () => {
    const nextRole =
      messages.length > 0 && messages[messages.length - 1].role === 'user'
        ? 'assistant'
        : 'user';
    setMessages((prev) => [
      ...prev,
      {
        id: Math.random().toString(36).substring(2, 9),
        role: nextRole,
        content: '',
      },
    ]);
  };

  const removeMessage = (id: string) => {
    if (messages.length <= 1) return;
    setMessages((prev) => prev.filter((m) => m.id !== id));
  };

  const updateMessage = (id: string, field: 'role' | 'content', value: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, [field]: value } : m))
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionId.trim() || !userId.trim() || !startedAt.trim()) {
      addToast('warning', 'Validation Error', 'Please specify Session ID, User ID, and Started At.');
      return;
    }

    const validMessages = messages.filter((m) => m.content.trim());
    if (validMessages.length === 0) {
      addToast('warning', 'Missing Messages', 'Please provide at least one message with content.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        session_id: sessionId.trim(),
        user_id: userId.trim(),
        started_at: startedAt.trim(),
        messages: validMessages.map((m) => ({
          role: m.role,
          content: m.content.trim(),
        })),
      };

      const result = await api.ingestSession(payload);
      setLastIngestResult(result);
      addToast('success', 'Ingestion Complete', `Session "${sessionId}" successfully stored in HydraDB.`);
    } catch (err: any) {
      addToast('error', 'Ingestion Failed', err?.message || 'Could not ingest session.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 sm:p-8 space-y-8 animate-[fadeIn_0.3s_ease-out]">
      {/* Header */}
      <div className="glass-card p-6 sm:p-8 border border-white/[0.08] bg-gradient-to-r from-emerald-500/[0.08] via-slate-900/60 to-slate-900/80">
        <div className="max-w-3xl space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 text-xs font-semibold">
            <Upload size={13} />
            <span>HydraDB Graph Ingestion Pipeline</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Ingest Conversation Session
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            Feed multi-turn dialogue into the MemoryGraph extraction pipeline to create Session anchors, extracted Fact nodes, Entity mappings, and automatic SUPERSEDES relations in HydraDB.
          </p>
        </div>
      </div>

      {/* Preset Demo Sample Sessions */}
      <div className="space-y-2.5">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
          <Sparkles size={13} className="text-amber-400" />
          PRESET DEMO DATASETS (CLICK TO LOAD)
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {sampleTemplates.map((tpl, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleLoadSample(tpl)}
              className="p-3.5 rounded-xl glass-card text-left hover:border-amber-500/40 hover:bg-slate-900/90 transition-all group"
            >
              <p className="text-xs font-bold text-slate-200 group-hover:text-amber-300 transition-colors">
                {tpl.name}
              </p>
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                {tpl.session_id} • {tpl.messages.length} msgs
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Main Ingest Form */}
      <form onSubmit={handleSubmit} className="glass-card p-6 space-y-6">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono pb-2 border-b border-white/5">
          SESSION METADATA
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Session ID *</label>
            <input
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              placeholder="e.g. alex-session-1"
              className="input-field text-xs font-mono"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">User ID *</label>
            <input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="e.g. alex"
              className="input-field text-xs font-mono"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Started At *</label>
            <input
              value={startedAt}
              onChange={(e) => setStartedAt(e.target.value)}
              placeholder="2024-01-10T10:00:00Z"
              className="input-field text-xs font-mono"
              required
            />
          </div>
        </div>

        {/* Dynamic Messages Builder */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              CONVERSATION MESSAGES ({messages.length})
            </label>
            <button
              type="button"
              onClick={addMessage}
              className="btn-secondary text-xs py-1 px-2.5"
            >
              <Plus size={13} />
              <span>Add Message</span>
            </button>
          </div>

          <div className="space-y-3">
            {messages.map((msg, idx) => (
              <div
                key={msg.id}
                className="flex gap-2.5 items-start p-3 rounded-xl bg-slate-950/60 border border-white/[0.06] animate-[fadeInUp_0.2s_ease-out]"
              >
                <div className="w-28 flex-shrink-0">
                  <select
                    value={msg.role}
                    onChange={(e) => updateMessage(msg.id, 'role', e.target.value as 'user' | 'assistant')}
                    className="input-field text-xs py-1.5 font-semibold capitalize"
                  >
                    <option value="user">User</option>
                    <option value="assistant">Assistant</option>
                  </select>
                </div>

                <div className="flex-1">
                  <textarea
                    value={msg.content}
                    onChange={(e) => updateMessage(msg.id, 'content', e.target.value)}
                    placeholder={`Message ${idx + 1} content...`}
                    rows={2}
                    className="input-field text-xs resize-none"
                    required
                  />
                </div>

                <button
                  type="button"
                  onClick={() => removeMessage(msg.id)}
                  disabled={messages.length <= 1}
                  className="p-2 text-slate-500 hover:text-rose-400 disabled:opacity-20 transition-colors"
                  title="Remove message"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Submit Actions */}
        <div className="pt-3 flex items-center justify-between border-t border-white/5">
          <span className="text-[11px] text-slate-500 font-mono">
            Sends payload to POST /ingest/session
          </span>
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary text-xs"
          >
            {submitting ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />}
            <span>{submitting ? 'Ingesting into HydraDB...' : 'Ingest Session'}</span>
          </button>
        </div>
      </form>

      {/* Ingestion Response View */}
      {lastIngestResult && (
        <div className="glass-card p-5 space-y-2.5 border-emerald-500/30 bg-emerald-500/[0.03] animate-[fadeIn_0.2s_ease-out]">
          <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs">
            <CheckCircle2 size={16} />
            <span>Session Ingestion Result</span>
          </div>
          <pre className="p-3.5 rounded-xl bg-black/60 border border-white/[0.08] text-[11px] text-emerald-300 font-mono overflow-x-auto">
            {JSON.stringify(lastIngestResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default IngestPage;
