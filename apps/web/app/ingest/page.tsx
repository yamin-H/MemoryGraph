'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { addToast } from '@/lib/hooks';
import { Upload, Plus, Trash2, Loader2, Sparkles, CheckCircle2, FileJson } from 'lucide-react';

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
    name: 'Session 2: Relocation & Pet Update',
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
  const [seedingBatch, setSeedingBatch] = useState(false);
  const [lastIngestResult, setLastIngestResult] = useState<any>(null);

  const handleSeedFullStory = async () => {
    setSeedingBatch(true);
    try {
      const resp = await api.seedDemoDataset();
      setLastIngestResult(resp);
      addToast('success', 'Full Dataset Seeded', resp.message || 'Seeded 35 sessions into HydraDB.');
    } catch (err: any) {
      addToast('error', 'Seeding Failed', err?.message || 'Could not seed batch dataset.');
    } finally {
      setSeedingBatch(false);
    }
  };

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
      addToast('success', 'Ingestion Complete', `Session "${sessionId}" stored in HydraDB.`);
    } catch (err: any) {
      addToast('error', 'Ingestion Failed', err?.message || 'Could not ingest session.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="text-center space-y-3 max-w-2xl mx-auto pt-2">
        <div className="animate-fade-in-up stagger-1 inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-700 dark:text-emerald-400 text-xs font-bold font-mono shadow-sm">
          <Upload size={14} className="text-emerald-500" />
          <span>HydraDB Graph Ingestion Pipeline</span>
        </div>
        <h1 className="animate-fade-in-up stagger-2 text-2xl sm:text-4xl font-black text-slate-900 dark:text-white tracking-tight font-heading">
          Ingest Conversation Session
        </h1>
        <p className="animate-fade-in-up stagger-3 text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed max-w-lg mx-auto font-medium">
          Feed multi-turn dialogue into the extraction pipeline to create Session anchors, Fact nodes, Entity mappings, and automatic SUPERSEDES relations.
        </p>
      </div>

      {/* 1-Click Story Seed Banner */}
      <div className="p-6 rounded-3xl bg-gradient-to-r from-amber-500/10 via-emerald-500/10 to-indigo-500/10 border border-amber-500/20 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg animate-fade-in-up stagger-4">
        <div className="space-y-1 text-center sm:text-left">
          <div className="flex items-center justify-center sm:justify-start gap-2 text-amber-600 dark:text-amber-400 font-bold text-sm">
            <Sparkles size={16} />
            <span>Seed 35-Session Alex Story Arc</span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 max-w-md">
            Automatically populate 35 multi-turn dialogues across 6 months with 115 facts and 67 <code className="text-rose-500 font-mono font-bold">SUPERSEDES</code> edges into HydraDB.
          </p>
        </div>
        <button
          type="button"
          onClick={handleSeedFullStory}
          disabled={seedingBatch}
          className="btn-primary text-xs px-5 py-2.5 flex-shrink-0 cursor-pointer shadow-md whitespace-nowrap"
        >
          {seedingBatch ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          <span>{seedingBatch ? 'Seeding 35 Sessions...' : '1-Click Seed HydraDB'}</span>
        </button>
      </div>

      {/* Preset Templates */}
      <div className="space-y-3 animate-fade-in-up stagger-4">
        <div className="section-label">
          <Sparkles size={13} className="text-amber-500" />
          <span>Preset Individual Sessions</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {sampleTemplates.map((tpl, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleLoadSample(tpl)}
              className="feature-card text-left group cursor-pointer shadow-md hover:border-amber-500/40 transition-all"
            >
              <p className="text-xs sm:text-sm font-bold text-slate-800 dark:text-slate-200 group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors duration-300 font-heading">
                {tpl.name}
              </p>
              <p className="text-[11px] text-slate-500 font-mono mt-1 font-semibold">
                {tpl.session_id} · {tpl.messages.length} messages
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Ingest Form */}
      <form onSubmit={handleSubmit} className="glass-panel !p-6 sm:!p-8 space-y-6 animate-fade-in-up stagger-5 rounded-3xl border border-slate-200 dark:border-white/[0.08] shadow-xl">
        <div className="section-label pb-2 border-b border-slate-200 dark:border-white/[0.06]">
          Session Metadata
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-600 dark:text-slate-400 mb-1.5">Session ID *</label>
            <input
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              placeholder="e.g. alex-session-1"
              className="input-field text-xs font-mono shadow-sm"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-600 dark:text-slate-400 mb-1.5">User ID *</label>
            <input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="e.g. alex"
              className="input-field text-xs font-mono shadow-sm"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-600 dark:text-slate-400 mb-1.5">Started At *</label>
            <input
              value={startedAt}
              onChange={(e) => setStartedAt(e.target.value)}
              placeholder="2024-01-10T10:00:00Z"
              className="input-field text-xs font-mono shadow-sm"
              required
            />
          </div>
        </div>

        {/* Messages Builder */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <div className="section-label">
              Messages ({messages.length})
            </div>
            <button
              type="button"
              onClick={addMessage}
              className="btn-secondary text-xs py-1.5 px-3.5 shadow-sm cursor-pointer"
            >
              <Plus size={13} />
              <span>Add Message</span>
            </button>
          </div>

          <div className="space-y-3">
            {messages.map((msg, idx) => (
              <div
                key={msg.id}
                className="flex gap-3 items-start p-3.5 rounded-2xl bg-slate-50 dark:bg-black/30 border border-slate-200 dark:border-white/[0.06] shadow-sm animate-fade-in"
              >
                <div className="w-28 flex-shrink-0">
                  <select
                    value={msg.role}
                    onChange={(e) => updateMessage(msg.id, 'role', e.target.value as 'user' | 'assistant')}
                    className="input-field text-xs py-2 font-bold capitalize cursor-pointer shadow-none"
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
                    className="input-field text-xs resize-none shadow-none font-medium"
                    required
                  />
                </div>

                <button
                  type="button"
                  onClick={() => removeMessage(msg.id)}
                  disabled={messages.length <= 1}
                  className="p-2 text-slate-400 hover:text-rose-500 disabled:opacity-20 transition-colors cursor-pointer rounded-lg hover:bg-slate-100 dark:hover:bg-white/5"
                  title="Remove message"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Submit */}
        <div className="pt-4 flex items-center justify-between border-t border-slate-200 dark:border-white/[0.06]">
          <span className="text-[11px] text-slate-500 font-mono font-semibold">
            POST /ingest/session
          </span>
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary text-xs px-6 py-2.5 shadow-md"
          >
            {submitting ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />}
            <span>{submitting ? 'Ingesting Session...' : 'Ingest Session'}</span>
          </button>
        </div>
      </form>

      {/* Result */}
      {lastIngestResult && (
        <div className="feature-card !border-emerald-500/25 space-y-3 animate-fade-in shadow-xl">
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-bold text-xs sm:text-sm">
            <CheckCircle2 size={16} />
            <span>Ingestion Result Payload</span>
          </div>
          <pre className="p-4 rounded-2xl bg-[#0b0f19] border border-slate-800 text-xs text-emerald-300 font-mono overflow-x-auto leading-relaxed">
            {JSON.stringify(lastIngestResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default IngestPage;
