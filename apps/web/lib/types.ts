export interface Message {
  role: 'user' | 'assistant';
  content: string;
  confidence?: number;
  abstained?: boolean;
  abstentionReason?: string;
  sourceSessions?: string[];
  supersededFacts?: Array<{ fact_id: string; content: string }>;
  reasoning?: string;
  queryTimeMs?: number;
  groqTokensUsed?: number;
  timestamp: Date;
}

export interface HealthStatus {
  status: string;
  services?: {
    api?: { status: string };
    hydradb?: { status: string };
    redis?: { status: string };
    groq?: { status: string };
  };
  facts_stored?: number;
  sessions_ingested?: number;
  entities_tracked?: number;
  avg_query_latency_ms?: number;
}

export interface Metrics {
  total_facts_stored: number;
  sessions_ingested: number;
  entities_tracked: number;
  avg_query_latency_ms: number;
  total_queries?: number;
  total_ingestions?: number;
  total_groq_tokens_used?: number;
  abstention_rate?: number;
}

export interface Fact {
  fact_id: string | number;
  content: string;
  entity_name?: string;
  entity_type?: string;
  confidence?: number;
  created_at?: string;
  is_current?: boolean;
  session_id?: string;
}

export interface Entity {
  entity_name: string;
  current_facts: Fact[];
  historical_facts: Fact[];
  invalidated_facts: Fact[];
  total_facts: number;
  user_id?: string;
  status?: string;
}

export interface GraphNode {
  id: string | number;
  label: string;
  type: 'Session' | 'Fact' | 'Entity' | 'Summary' | 'Message';
  data?: any;
  color?: string;
  val?: number;
}

export interface GraphEdge {
  source: string | number;
  target: string | number;
  type: string;
  color?: string;
  width?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface QueryResponse {
  answer: string;
  confidence: number;
  abstained: boolean;
  abstention_reason?: string;
  source_sessions: string[];
  superseded_facts: Array<{ fact_id: string; content: string }>;
  reasoning: string;
  query_time_ms: number;
  facts_examined: number;
  groq_tokens_used: number;
  user_id: string;
}

export interface DatasetInfo {
  id: string;
  name: string;
  description: string;
  file: string;
  exists: boolean;
  size_mb: number;
  total_examples: number;
}

export interface DatasetSample {
  question_id: string;
  question_type: string;
  question: string;
  answer: string;
  question_date?: string;
  sessions_count: number;
  has_abstention: boolean;
}

export interface SampleEvaluationResult {
  question_id: string;
  question: string;
  ground_truth: string;
  predicted_answer: string;
  confidence: number;
  abstained: boolean;
  is_correct: boolean;
  exact_match: boolean;
  contains_answer: boolean;
  query_time_ms: number;
  ingestion_time_ms: number;
  sessions_evaluated: number;
  reasoning?: string;
  source_sessions?: string[];
}

export interface SessionItem {
  id: string;
  user_id: string;
  date: string;
  summary?: string;
  factCount: number;
}

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}
