import { useEffect, useState, useCallback, useRef } from 'react';
import { api } from './api';
import { HealthStatus, Metrics, Toast, ToastType } from './types';

export function useHealth(interval: number = 30000) {
  const [health, setHealth] = useState<HealthStatus>({ status: 'unknown' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const data = await api.getHealth();
      setHealth(data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch health status');
      console.error('Error fetching health:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const timer = setInterval(fetchHealth, interval);
    return () => clearInterval(timer);
  }, [fetchHealth, interval]);

  return { health, loading, error, refetch: fetchHealth };
}

export function useMetrics(interval: number = 10000) {
  const [metrics, setMetrics] = useState<Metrics>({
    total_facts_stored: 0,
    sessions_ingested: 0,
    entities_tracked: 0,
    avg_query_latency_ms: 0,
    total_queries: 0,
    total_ingestions: 0,
    total_groq_tokens_used: 0,
    abstention_rate: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      const data = await api.getMetrics();
      setMetrics(data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch metrics');
      console.error('Error fetching metrics:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    const timer = setInterval(fetchMetrics, interval);
    return () => clearInterval(timer);
  }, [fetchMetrics, interval]);

  return { metrics, loading, error, refetch: fetchMetrics };
}

// Global Toast state management
let toastListeners: Array<(toasts: Toast[]) => void> = [];
let toastStore: Toast[] = [];

function notifyListeners() {
  toastListeners.forEach((listener) => listener([...toastStore]));
}

export function addToast(type: ToastType, title: string, message?: string, duration = 4500) {
  const id = Math.random().toString(36).substring(2, 9);
  const toast: Toast = { id, type, title, message, duration };
  toastStore = [...toastStore, toast];
  notifyListeners();
  if (duration > 0) {
    setTimeout(() => removeToast(id), duration);
  }
  return id;
}

export function removeToast(id: string) {
  toastStore = toastStore.filter((t) => t.id !== id);
  notifyListeners();
}

export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    toastListeners.push(setToasts);
    setToasts([...toastStore]);
    return () => {
      toastListeners = toastListeners.filter((l) => l !== setToasts);
    };
  }, []);

  return { toasts, addToast, removeToast };
}

export function useAnimatedCounter(target: number, duration: number = 700) {
  const [value, setValue] = useState(0);
  const prevTarget = useRef(0);

  useEffect(() => {
    const start = prevTarget.current;
    const diff = target - start;
    if (diff === 0) {
      setValue(target);
      return;
    }
    const startTime = performance.now();
    let raf: number;

    const step = (time: number) => {
      const elapsed = time - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // Cubic ease out
      setValue(Math.round(start + diff * eased));
      if (progress < 1) {
        raf = requestAnimationFrame(step);
      } else {
        prevTarget.current = target;
      }
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return value;
}
