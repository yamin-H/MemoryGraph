import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  HealthStatus,
  Metrics,
  QueryResponse,
  Entity,
  GraphData,
  DatasetInfo,
  DatasetSample,
  SampleEvaluationResult,
  SessionItem,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 800;
const REQUEST_TIMEOUT_MS = 30000;

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

class MemoryGraphAPI {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: REQUEST_TIMEOUT_MS,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        const message = error.response
          ? `[API ${error.response.status}] ${(error.response.data as any)?.detail || error.message}`
          : `[Network Error] ${error.message}`;
        console.warn(message);
        return Promise.reject(error);
      }
    );
  }

  private async withRetry<T>(fn: () => Promise<T>, retries = MAX_RETRIES): Promise<T> {
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        return await fn();
      } catch (error) {
        const axiosError = error as AxiosError;
        const status = axiosError.response?.status;
        const isRetryable = !status || status >= 500 || status === 429;
        if (attempt === retries || !isRetryable) throw error;
        await sleep(RETRY_DELAY_MS * Math.pow(2, attempt));
      }
    }
    throw new Error('Max retries exceeded');
  }

  async getHealth(): Promise<HealthStatus> {
    try {
      const response = await this.withRetry(() => this.client.get('/health'));
      return response.data;
    } catch {
      return { status: 'unhealthy' };
    }
  }

  async getMetrics(): Promise<Metrics> {
    try {
      const response = await this.withRetry(() => this.client.get('/metrics'));
      return response.data;
    } catch {
      return {
        total_facts_stored: 0,
        sessions_ingested: 0,
        entities_tracked: 0,
        avg_query_latency_ms: 0,
        total_queries: 0,
        total_ingestions: 0,
        total_groq_tokens_used: 0,
        abstention_rate: 0,
      };
    }
  }

  async queryMemory(question: string, userId: string = 'user'): Promise<QueryResponse> {
    const response = await this.withRetry(() =>
      this.client.post('/query', { question, user_id: userId })
    );
    return response.data;
  }

  async getSessionGraph(sessionId: string): Promise<GraphData> {
    try {
      const response = await this.withRetry(() =>
        this.client.get(`/graph/session/${sessionId}`)
      );
      return response.data;
    } catch {
      return { nodes: [], edges: [] };
    }
  }

  async getEntityGraph(entityName: string): Promise<GraphData> {
    try {
      const response = await this.withRetry(() =>
        this.client.get(`/graph/entity/${entityName}`)
      );
      return response.data;
    } catch {
      return { nodes: [], edges: [] };
    }
  }

  async getAllGraphs(): Promise<GraphData> {
    try {
      const response = await this.withRetry(() =>
        this.client.get('/graph/all')
      );
      return response.data;
    } catch {
      return { nodes: [], edges: [] };
    }
  }

  async getRecentSessions(limit: number = 50): Promise<SessionItem[]> {
    try {
      const response = await this.withRetry(() =>
        this.client.get('/graph/sessions', { params: { limit } })
      );
      return response.data || [];
    } catch {
      return [];
    }
  }

  async ingestSession(session: {
    session_id: string;
    user_id: string;
    started_at: string;
    messages: Array<{ role: string; content: string }>;
  }): Promise<any> {
    const response = await this.withRetry(() =>
      this.client.post('/ingest/session', session)
    );
    return response.data;
  }

  async ingestBatch(sessions: any[]): Promise<any> {
    const response = await this.withRetry(() =>
      this.client.post('/ingest/batch', sessions)
    );
    return response.data;
  }

  // Benchmark & Datasets endpoints
  async getBenchmarkDatasets(): Promise<DatasetInfo[]> {
    try {
      const response = await this.withRetry(() =>
        this.client.get('/benchmark/datasets')
      );
      return response.data || [];
    } catch {
      return [];
    }
  }

  async getDatasetSamples(
    datasetId: string = 'longmemeval',
    limit: number = 20,
    offset: number = 0,
    questionType?: string
  ): Promise<{ dataset_id: string; total: number; samples: DatasetSample[] }> {
    try {
      const response = await this.withRetry(() =>
        this.client.get(`/benchmark/dataset/${datasetId}/samples`, {
          params: { limit, offset, question_type: questionType },
        })
      );
      return response.data || { dataset_id: datasetId, total: 0, samples: [] };
    } catch {
      return { dataset_id: datasetId, total: 0, samples: [] };
    }
  }

  async evaluateSample(
    datasetId: string,
    questionId: string,
    autoIngest: boolean = false
  ): Promise<SampleEvaluationResult> {
    const response = await this.withRetry(() =>
      this.client.post('/benchmark/evaluate-sample', {
        dataset_id: datasetId,
        question_id: questionId,
        auto_ingest: autoIngest,
      })
    );
    return response.data;
  }

  async runBenchmark(): Promise<{ status: string; job_id: string; message: string }> {
    const response = await this.withRetry(() =>
      this.client.post('/benchmark/run')
    );
    return response.data;
  }

  async getBenchmarkJob(jobId: string): Promise<{
    job_id: string;
    status: 'running' | 'completed' | 'failed';
    start_time: number;
    end_time?: number;
    total_duration_ms?: number;
    tests?: Array<{
      question_id: string;
      question: string;
      ground_truth: string;
      predicted: string;
      is_correct: boolean;
      duration_ms: number;
    }>;
  }> {
    const response = await this.withRetry(() =>
      this.client.get(`/benchmark/job/${jobId}`)
    );
    return response.data;
  }

  async getBenchmarkResults(): Promise<any> {
    try {
      const response = await this.withRetry(() =>
        this.client.get('/benchmark/results')
      );
      return response.data;
    } catch {
      return {};
    }
  }
}

export const api = new MemoryGraphAPI();
export default api;
