/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type MemoryLayer = 'L0' | 'constraints' | 'procedures' | 'continuity' | 'facts';

export interface MemoryEntry {
  id: string;
  title: string;
  content: string;
  layer: MemoryLayer;
  kind: string;
  source: string;
  sessionId?: string;
  tags: string[];
  confidence: number;
  updatedAt: string;
  status: 'active' | 'archived' | 'disabled';
}

export interface UpstreamConfig {
  id: string;
  name: string;
  provider: string;
  baseUrl: string;
  apiKey: string;
  defaultModel: string;
  isDefault: boolean;
  isEnabled: boolean;
  type: 'TARGET' | 'LLMAPI_LEGACY';
  latency?: number;
}

export interface RequestTrace {
  id: string;
  sessionId: string;
  timestamp: string;
  provider: string;
  model: string;
  latency: number;
  status: 'success' | 'error' | 'fallback';
  fallback: boolean;
  trim: number;
  rewrite: boolean;
  unsupported_ratio: number;
  details: {
    originalInput: string;
    routeDecision: string;
    selectedProviderModel: string;
    fallbackChain: string[];
    memoryHitSummary: string[];
    trimReport: string;
    groundingSummary: string;
    rewriteDiff: string;
    finalResponse: string;
  };
}

export interface DashboardStats {
  serviceStatus: 'online' | 'degraded' | 'offline';
  activeUpstream: string;
  activeModel: string;
  totalRequests: number;
  avgLatency: number;
  fallbackCount: number;
  tokensTotal: number;
  tokensSaved: number;
  savingRate: number;
}
