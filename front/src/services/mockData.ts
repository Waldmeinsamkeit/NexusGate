/**
 * NEXUSGATE FRONTEND MOCK DATA
 * 
 * IMPORTANT: In a production environment, all data exported from this file 
 * should be replaced by real-time data fetched from the NexusGate Backend API.
 * 
 * Recommended Integration Strategy:
 * 1. Define corresponding API services in `src/services/api.ts`.
 * 2. Use React dynamic state (useState/useEffect) at the component level to replace these constants.
 * 3. Implement SWR or React Query for robust data fetching and caching.
 */

import { MemoryEntry, UpstreamConfig, RequestTrace, DashboardStats } from '../types';

export const mockStats: DashboardStats = {
  serviceStatus: 'online',
  activeUpstream: 'OpenAI (Primary)',
  activeModel: 'gpt-4o',
  totalRequests: 12450,
  avgLatency: 840,
  fallbackCount: 12,
  tokensTotal: 5800000,
  tokensSaved: 1200000,
  savingRate: 0.207,
};

export const mockUpstreams: UpstreamConfig[] = [
  {
    id: '1',
    name: 'OpenAI Primary',
    provider: 'openai',
    baseUrl: 'https://api.openai.com/v1',
    apiKey: 'sk-proj-****************',
    defaultModel: 'gpt-4o',
    isDefault: true,
    isEnabled: true,
    type: 'TARGET',
    latency: 240,
  },
  {
    id: '2',
    name: 'Anthropic Fallback',
    provider: 'anthropic',
    baseUrl: 'https://api.anthropic.com',
    apiKey: 'sk-ant-****************',
    defaultModel: 'claude-3-5-sonnet',
    isDefault: false,
    isEnabled: true,
    type: 'TARGET',
    latency: 320,
  },
  {
    id: '3',
    name: 'Legacy API',
    provider: 'openai',
    baseUrl: 'https://legacy-proxy.internal',
    apiKey: 'old-key-***********',
    defaultModel: 'gpt-3.5-turbo',
    isDefault: false,
    isEnabled: true,
    type: 'LLMAPI_LEGACY',
  },
];

export const mockMemories: MemoryEntry[] = [
  {
    id: 'mem_1',
    title: 'Project Architecture Guidelines',
    content: 'Always use modular architecture for microservices. Ensure all APIs are documented with OpenAPI 3.0.',
    layer: 'procedures',
    kind: 'guideline',
    source: 'manual_entry',
    tags: ['arch', 'standard'],
    confidence: 0.95,
    updatedAt: '2024-03-20T10:00:00Z',
    status: 'active',
  },
  {
    id: 'mem_2',
    title: 'Deployment Server IP',
    content: 'Production server is located at 192.168.1.100.',
    layer: 'facts',
    kind: 'fact',
    source: 'session_extract',
    sessionId: 'sess_99',
    tags: ['infra', 'prod'],
    confidence: 1.0,
    updatedAt: '2024-03-21T15:30:00Z',
    status: 'active',
  },
  {
    id: 'mem_3',
    title: 'Tone Preference',
    content: 'User prefers a technical but concise communication style.',
    layer: 'constraints',
    kind: 'preference',
    source: 'inference',
    tags: ['user', 'style'],
    confidence: 0.85,
    updatedAt: '2024-03-19T08:00:00Z',
    status: 'active',
  },
];

export const mockTraces: RequestTrace[] = [
  {
    id: 'req_001',
    sessionId: 'sess_9921',
    timestamp: new Date().toISOString(),
    provider: 'OpenAI',
    model: 'gpt-4o',
    latency: 840,
    status: 'success',
    fallback: false,
    trim: 240,
    rewrite: true,
    unsupported_ratio: 0.02,
    details: {
      originalInput: '请帮我梳理一下项目的微服务架构，并且导出为 Mermaid 格式。',
      routeDecision: '命中元规则：优先高性能模型 GPT-4o。',
      selectedProviderModel: 'OpenAI / gpt-4o',
      fallbackChain: [],
      memoryHitSummary: ['Architecture_Standard_v2', 'Mermaid_Template_Core'],
      trimReport: '检测到重复上下文引用，已裁剪 240 Tokens 以优化首字延迟。',
      groundingSummary: '所有语义声明均已匹配知识库。安全性检测通过。',
      rewriteDiff: '- 请帮我梳理一下项目的微服务架构...\n+ 作为架构专家，请基于 NexusGate 2.0 标准梳理微服务架构...',
      finalResponse: '好的，基于项目的 NexusGate 2.0 架构标准，以下是微服务架构梳理及 Mermaid 图表：\n\ngraph TD\n  A[API Gateway] --> B[Auth Service]',
    }
  },
  {
    id: 'req_002',
    sessionId: 'sess_9922',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    provider: 'Anthropic',
    model: 'claude-3-5-sonnet',
    latency: 2100,
    status: 'fallback',
    fallback: true,
    trim: 0,
    rewrite: false,
    unsupported_ratio: 0.15,
    details: {
      originalInput: '分析这段 2048 长度的日志，查找内存泄漏的可能原因。',
      routeDecision: 'OpenAI 主节点超时 (5s)，自动触发 Fallback 机制。',
      selectedProviderModel: 'Anthropic / claude-3-5-sonnet',
      fallbackChain: ['OpenAI'],
      memoryHitSummary: ['Log_Analysis_Procedures'],
      trimReport: '长度未超过阈值，未执行裁剪。',
      groundingSummary: '检测到 2 处未经验证的内存地址推断，已在响应中增加警示标注。',
      rewriteDiff: '原样转发，未重写。',
      finalResponse: '经过日志分析，内存泄漏可能发生在第 452 行的 Buffer 指向... 注意：部分推断基于启发式算法。',
    }
  }
];
