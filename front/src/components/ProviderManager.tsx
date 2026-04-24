import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'motion/react';
import {
  RefreshCw,
  AlertCircle,
  Check,
  Zap,
  Globe,
  ArrowRightLeft,
  ExternalLink,
} from 'lucide-react';
import {
  fetchConfig,
  updateConfig,
  testConnection,
  type AdminConfig,
  type TestResult,
} from '../services/api';
import { cn } from '../lib/utils';

/* ── provider presets ────────────────────────────────────────── */

interface ProviderPreset {
  id: string;
  name: string;
  provider: string;
  baseUrl: string;
  defaultModel: string;
  models: string[];
  color: string;
  bgColor: string;
  borderColor: string;
  docs: string;
}

const PROVIDER_GROUPS: { label: string; presets: ProviderPreset[] }[] = [
  {
    label: 'Claude (Anthropic)',
    presets: [
      {
        id: 'claude-direct',
        name: 'Anthropic 直连',
        provider: 'anthropic',
        baseUrl: 'https://api.anthropic.com',
        defaultModel: 'claude-sonnet-4-5-20250929',
        models: ['claude-sonnet-4-5-20250929', 'claude-opus-4-20250514', 'claude-3-5-haiku-20241022'],
        color: 'text-orange-700',
        bgColor: 'bg-orange-50',
        borderColor: 'border-orange-200',
        docs: 'https://docs.anthropic.com',
      },
    ],
  },
  {
    label: 'Google (Gemini)',
    presets: [
      {
        id: 'gemini-direct',
        name: 'Google AI Studio',
        provider: 'gemini',
        baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
        defaultModel: 'gemini-2.5-pro',
        models: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash'],
        color: 'text-blue-700',
        bgColor: 'bg-blue-50',
        borderColor: 'border-blue-200',
        docs: 'https://ai.google.dev',
      },
      {
        id: 'vertex-ai',
        name: 'Vertex AI',
        provider: 'vertex_ai',
        baseUrl: '',
        defaultModel: 'gemini-2.5-pro',
        models: ['gemini-2.5-pro', 'gemini-2.5-flash'],
        color: 'text-blue-700',
        bgColor: 'bg-blue-50',
        borderColor: 'border-blue-200',
        docs: 'https://cloud.google.com/vertex-ai',
      },
    ],
  },
  {
    label: 'OpenAI',
    presets: [
      {
        id: 'openai-direct',
        name: 'OpenAI 直连',
        provider: 'openai',
        baseUrl: 'https://api.openai.com/v1',
        defaultModel: 'gpt-4.1',
        models: ['gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano', 'o3', 'o4-mini'],
        color: 'text-green-700',
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
        docs: 'https://platform.openai.com',
      },
      {
        id: 'openrouter',
        name: 'OpenRouter',
        provider: 'openrouter',
        baseUrl: 'https://openrouter.ai/api/v1',
        defaultModel: 'anthropic/claude-sonnet-4',
        models: ['anthropic/claude-sonnet-4', 'google/gemini-2.5-pro', 'openai/gpt-4.1'],
        color: 'text-green-700',
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
        docs: 'https://openrouter.ai/docs',
      },
    ],
  },
];

/* ── main component ──────────────────────────────────────────── */

export const ProviderManager = ({ configVersion = 0, onConfigChanged }: { configVersion?: number; onConfigChanged?: () => void }) => {
  const [config, setConfig] = useState<AdminConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [switching, setSwitching] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testing, setTesting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const cfg = await fetchConfig();
      setConfig(cfg);
    } catch (e: any) {
      setError(e.message || '无法加载配置');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load, configVersion]);

  const handleSwitch = async (preset: ProviderPreset) => {
    if (!window.confirm(`确认切换上游到「${preset.name}」?\n\nProvider: ${preset.provider}\nBase URL: ${preset.baseUrl || '(provider direct)'}\nModel: ${preset.defaultModel}`)) return;
    setSwitching(preset.id);
    setTestResult(null);
    try {
      const res = await updateConfig({
        target_provider: preset.provider,
        target_base_url: preset.baseUrl || undefined,
        default_model: preset.defaultModel,
      });
      setConfig(res.config);
      onConfigChanged?.();
    } catch (e: any) {
      alert('切换失败: ' + (e.message || e));
    } finally {
      setSwitching(null);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testConnection();
      setTestResult(res);
    } catch (e: any) {
      setTestResult({ ok: false, status_code: 0, latency_ms: 0, model_count: 0, sample_models: [], error: e.message });
    } finally {
      setTesting(false);
    }
  };

  // Determine which preset is currently active
  const activePresetId = (() => {
    if (!config) return null;
    const p = config.target.provider?.toLowerCase() || '';
    const u = (config.effective.base_url || '').toLowerCase();
    for (const group of PROVIDER_GROUPS) {
      for (const preset of group.presets) {
        if (preset.provider === p || u.includes(preset.baseUrl.replace('https://', '').split('/')[0])) {
          return preset.id;
        }
      }
    }
    return null;
  })();

  if (error && !config) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle size={40} className="text-slate-300" />
        <p className="text-sm text-slate-500">{error}</p>
        <button onClick={load} className="text-xs text-blue-600 hover:underline">重试</button>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      {/* Header */}
      <header className="card-panel p-4 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-800">上游管理</h2>
          <p className="text-slate-400 text-[11px] font-medium uppercase tracking-tight">一键切换 LLM 上游服务商</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleTest}
            disabled={testing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold bg-white border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-700 disabled:opacity-50 transition-colors"
          >
            {testing ? <RefreshCw size={12} className="animate-spin" /> : <Zap size={12} />}
            测试当前连接
          </button>
          <button onClick={load} disabled={loading} className="p-1.5 hover:bg-slate-100 rounded-md text-slate-400 disabled:opacity-50">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </header>

      {/* Current active */}
      {config && (
        <div className="card-panel p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center">
              <Globe size={16} className="text-emerald-600" />
            </div>
            <div>
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">当前上游</h3>
              <p className="text-[10px] text-slate-400">活跃的上游服务配置</p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-[9px] text-slate-400 font-bold uppercase">Provider</span>
              <p className="font-mono font-bold text-slate-800 mt-1">{config.target.provider || '-'}</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-[9px] text-slate-400 font-bold uppercase">Base URL</span>
              <p className="font-mono text-blue-600 mt-1 truncate">{config.effective.base_url || '(provider direct)'}</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-[9px] text-slate-400 font-bold uppercase">默认模型</span>
              <p className="font-mono font-bold text-slate-800 mt-1">{config.target.default_model || '-'}</p>
            </div>
          </div>

          {/* Test result */}
          {testResult && (
            <div className={cn('mt-3 p-3 rounded-lg border text-xs', testResult.ok ? 'bg-emerald-50 border-emerald-100' : 'bg-red-50 border-red-100')}>
              <div className="flex items-center gap-2">
                {testResult.ok ? <Check size={14} className="text-emerald-600" /> : <AlertCircle size={14} className="text-red-600" />}
                <span className="font-bold">{testResult.ok ? '连接成功' : '连接失败'}</span>
                {testResult.latency_ms > 0 && <span className="text-slate-400 font-mono">{testResult.latency_ms.toFixed(0)}ms</span>}
              </div>
              {testResult.ok && testResult.sample_models.length > 0 && (
                <p className="text-slate-600 mt-1">可用模型: {testResult.sample_models.slice(0, 5).join(', ')}{testResult.model_count > 5 ? ` +${testResult.model_count - 5}` : ''}</p>
              )}
              {testResult.error && <p className="text-red-600 mt-1 break-all">{testResult.error}</p>}
            </div>
          )}
        </div>
      )}

      {/* Provider groups */}
      {PROVIDER_GROUPS.map((group) => (
        <div key={group.label} className="space-y-3">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest px-1">{group.label}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {group.presets.map((preset) => {
              const isActive = activePresetId === preset.id;
              const isSwitching = switching === preset.id;
              return (
                <div
                  key={preset.id}
                  className={cn(
                    'card-panel overflow-hidden transition-all',
                    isActive && 'ring-2 ring-blue-500/40 border-blue-300',
                  )}
                >
                  <div className="p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center', preset.bgColor)}>
                          <Globe size={14} className={preset.color} />
                        </div>
                        <div>
                          <h4 className="text-sm font-bold text-slate-800">{preset.name}</h4>
                          <p className="text-[9px] text-slate-400 font-mono">{preset.provider}</p>
                        </div>
                      </div>
                      {isActive && (
                        <span className="px-2 py-0.5 text-[9px] font-bold bg-blue-100 text-blue-700 rounded-full uppercase">当前</span>
                      )}
                    </div>

                    <div className="space-y-2 mb-4">
                      <div className="text-[10px]">
                        <span className="text-slate-400 font-bold uppercase">Base URL</span>
                        <p className="font-mono text-slate-600 mt-0.5 truncate">{preset.baseUrl || '(provider direct)'}</p>
                      </div>
                      <div className="text-[10px]">
                        <span className="text-slate-400 font-bold uppercase">可用模型</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {preset.models.map((m) => (
                            <span key={m} className="px-1.5 py-0.5 bg-slate-50 border border-slate-100 rounded text-[9px] font-mono text-slate-600">{m}</span>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleSwitch(preset)}
                        disabled={isActive || !!switching}
                        className={cn(
                          'flex-1 flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all',
                          isActive
                            ? 'bg-slate-100 text-slate-400 cursor-default'
                            : 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm disabled:opacity-50',
                        )}
                      >
                        {isSwitching ? (
                          <RefreshCw size={12} className="animate-spin" />
                        ) : isActive ? (
                          <Check size={12} />
                        ) : (
                          <ArrowRightLeft size={12} />
                        )}
                        {isActive ? '当前使用中' : '切换到此上游'}
                      </button>
                      <a
                        href={preset.docs}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
                        title="查看文档"
                      >
                        <ExternalLink size={14} />
                      </a>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </motion.div>
  );
};
