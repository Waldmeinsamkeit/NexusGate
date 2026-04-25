/**
 * NexusGate Admin API client
 * Communicates with the backend at /admin/* and /health endpoints.
 */

const API_KEY_STORAGE_KEY = 'nexusgate_api_key';

export function getApiKey(): string {
  return localStorage.getItem(API_KEY_STORAGE_KEY) || '';
}

export function setApiKey(key: string): void {
  localStorage.setItem(API_KEY_STORAGE_KEY, key);
}

function authHeaders(): Record<string, string> {
  const key = getApiKey();
  if (!key) return {};
  return { Authorization: `Bearer ${key}` };
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(options?.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json();
}

// ── Health ──────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  upstream: string;
  upstream_mode: string;
  auth_mode: string;
  local_key_source: string;
  sync_status: string;
  synced_clients: string[];
  sync_errors: string[];
}

export function fetchHealth(): Promise<HealthResponse> {
  return request('/health');
}

// ── Config ──────────────────────────────────────────────────────────

export interface AdminConfig {
  app: { name: string; env: string };
  target: {
    provider: string;
    base_url: string | null;
    api_key_masked: string;
    default_model: string;
  };
  legacy_llmapi: {
    base_url: string | null;
    api_key_masked: string;
    model_prefix: string;
    provider_prefix: string;
  };
  effective: {
    base_url: string | null;
    api_key_masked: string;
    upstream_mode: string;
  };
  history_rewrite: {
    enabled: boolean;
    default_mode: string;
    global_light_query_threshold: number;
    light: RewriteModeConfig;
    normal: RewriteModeConfig;
    heavy: RewriteModeConfig;
  };
  context_budget: {
    enabled: boolean;
    response_reserve_ratio: number;
    min_prompt_tokens: number;
  };
  health: HealthResponse;
}

export interface RewriteModeConfig {
  keep_system: number;
  keep_user: number;
  keep_assistant: number;
  keep_tool: number;
  keep_other: number;
  max_chars_per_message: number;
}

export function fetchConfig(): Promise<AdminConfig> {
  return request('/admin/config');
}

export interface ConfigUpdatePayload {
  target_provider?: string;
  target_base_url?: string;
  target_api_key?: string;
  default_model?: string;
  llmapi_base_url?: string;
  llmapi_api_key?: string;
  llmapi_model_prefix?: string;
  llmapi_provider_prefix?: string;
}

export function updateConfig(payload: ConfigUpdatePayload): Promise<{
  status: string;
  updated_keys: string[];
  config: AdminConfig;
}> {
  return request('/admin/config', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export interface TestResult {
  ok: boolean;
  status_code: number;
  latency_ms: number;
  model_count: number;
  sample_models: string[];
  error: string;
}

export function testConnection(): Promise<TestResult> {
  return request('/admin/config/test', { method: 'POST' });
}

export function fetchModels(): Promise<{
  ok: boolean;
  models: string[];
  error: string;
}> {
  return request('/admin/config/models');
}

// ── Memories ────────────────────────────────────────────────────────

export interface MemoryRecord {
  memory_id: string;
  layer: string;
  memory_type: string;
  scope: string;
  content: string;
  summary: string;
  evidence: string;
  evidence_ref: string;
  evidence_type: string;
  verified: boolean;
  confidence: number;
  dedupe_key: string;
  session_id: string;
  project_id: string;
  source: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  last_accessed_at: string;
  archived: boolean;
  supersedes: string;
}

export function fetchMemories(params?: {
  limit?: number;
  layers?: string;
  query?: string;
  include_archived?: boolean;
}): Promise<{ total: number; items: MemoryRecord[] }> {
  const qs = new URLSearchParams();
  if (params?.limit) qs.set('limit', String(params.limit));
  if (params?.layers) qs.set('layers', params.layers);
  if (params?.query) qs.set('query', params.query);
  if (params?.include_archived) qs.set('include_archived', 'true');
  const suffix = qs.toString() ? `?${qs}` : '';
  return request(`/admin/memories${suffix}`);
}

export function fetchMemoryDetail(id: string): Promise<{
  item: MemoryRecord;
  history: { version_index: number; updated_at: string; source: string; archived: boolean; content: string }[];
  history_count: number;
}> {
  return request(`/admin/memories/${id}`);
}

export function createMemory(payload: {
  content: string;
  layer: string;
  tags?: string[];
  verified?: boolean;
  l1_index?: string;
}): Promise<{ status: string; item?: MemoryRecord; items?: MemoryRecord[] }> {
  return request('/admin/memories', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateMemory(
  id: string,
  payload: Partial<Pick<MemoryRecord, 'content' | 'summary' | 'verified' | 'confidence' | 'tags' | 'archived' | 'layer'>>,
): Promise<{ status: string; item: MemoryRecord }> {
  return request(`/admin/memories/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function archiveMemory(id: string): Promise<{ status: string; memory_id: string; archived: boolean }> {
  return request(`/admin/memories/${id}`, { method: 'DELETE' });
}

export function archiveMemoryLayer(layer: string): Promise<{ status: string; layer: string; archived_count: number }> {
  return request(`/admin/memories-layer/${layer}`, { method: 'DELETE' });
}

// ── Traces ──────────────────────────────────────────────────────────

export interface TraceRecord {
  request_id: string;
  created_at: number;
  session_id: string;
  api_style: string;
  provider: string;
  model: string;
  status: string;
  fallback_count: number;
  has_trim: boolean;
  latency_ms: number;
  unsupported_ratio: number;
  token_stats: {
    estimated_prompt_tokens: number;
    estimated_sent_tokens: number;
    raw_input_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    saved_tokens_estimated: number;
    saved_tokens_actual: number;
    saved_rate_estimated: number;
    saved_rate_actual: number;
    usage_source: string;
  };
  budget_diagnostics?: Record<string, unknown>;
  trace: {
    history?: {
      raw_input_tokens?: number;
      prepared_messages_tokens?: number;
      history_replaced_tokens?: number;
      mode?: string;
    };
    retrieval?: {
      raw_candidates?: number;
      kept_candidates?: number;
      dropped_candidates?: number;
      dropped_reasons?: string[];
      memory_budget_tokens?: number;
      memory_budget_chars?: number;
    };
    assembly?: {
      facts_count?: number;
      procedures_count?: number;
      continuity_count?: number;
      constraints_count?: number;
    };
    render?: {
      mode?: string;
      final_render_strategy?: string;
      budget_before?: number;
      budget_after?: number;
      estimated_tokens_before?: number;
      estimated_tokens_after?: number;
      trimmed_total_chars?: number;
      final_total_chars?: number;
      trim_passes?: number;
      dropped_blocks?: string[];
      dropped_block_ids?: string[];
      drop_reason_by_block?: Record<string, string>;
      drop_reasons?: string[];
      rendered_block_order?: string[];
      retained_counts_by_section?: Record<string, number>;
      retained_fact_ids?: string[];
      retained_procedure_ids?: string[];
      retained_continuity_ids?: string[];
      retained_constraint_ids?: string[];
      trimmed_l1_chars?: number;
      trimmed_l2_chars?: number;
      trimmed_l3_chars?: number;
      trimmed_l4_chars?: number;
      sections_after?: Record<string, string>;
    };
    budget?: {
      enabled?: boolean;
      native_tools_budget?: boolean;
      before_tokens?: number;
      after_tokens?: number;
      context_budget_tokens?: number;
      prompt_budget_tokens?: number;
      truncated_messages?: number;
      dropped_messages?: number;
      over_budget_before?: boolean;
      over_budget_after?: boolean;
      skipped?: boolean;
      skip_reason?: string;
      episode_count?: number;
      episodes_trimmed?: number;
      episodes_summarized?: number;
      tool_result_pruned_chars?: number;
    };
    routing?: {
      provider?: string;
      model?: string;
      reason_codes?: string[];
      fallback_chain?: string[];
      context_budget?: number;
      grounding_mode?: string;
      grounding_policy?: string;
    };
    fallback?: Array<Record<string, unknown>>;
    route_decision?: string;
  };
  error?: string;
}

export function fetchTraces(limit = 50): Promise<{ total: number; items: TraceRecord[] }> {
  return request(`/admin/traces?limit=${limit}`);
}
