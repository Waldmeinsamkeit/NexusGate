import { useState, useEffect, useCallback } from 'react';
import { motion } from 'motion/react';
import {
  Save,
  RefreshCw,
  AlertCircle,
  Check,
  Zap,
  Server,
  Copy,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronUp,
  Terminal,
} from 'lucide-react';
import {
  fetchConfig,
  updateConfig,
  testConnection,
  getApiKey,
  setApiKey,
  type AdminConfig,
  type TestResult,
} from '../services/api';
import { cn } from '../lib/utils';

/* ── field row ─────────────────────────────────────────────────── */

const Field = ({ label, children }: { label: string; children: import('react').ReactNode }) => (
  <div className="space-y-1.5">
    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{label}</label>
    {children}
  </div>
);

const inputCls = 'w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none font-mono';

/* ── main ──────────────────────────────────────────────────────── */

export const Settings = ({ onConfigChanged }: { onConfigChanged?: () => void }) => {
  const [config, setConfig] = useState<AdminConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [showGuide, setShowGuide] = useState(false);

  // Form state (editable fields)
  const [provider, setProvider] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKeyValue, setApiKeyValue] = useState('');
  const [defaultModel, setDefaultModel] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);

  // Local admin key
  const [localKey, setLocalKey] = useState(getApiKey());

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const cfg = await fetchConfig();
      setConfig(cfg);
      setProvider(cfg.target.provider || '');
      setBaseUrl(cfg.target.base_url || '');
      setApiKeyValue('');
      setDefaultModel(cfg.target.default_model || '');
    } catch (e: any) {
      setError(e.message || '无法加载配置');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: Record<string, string> = {};
      if (provider) payload.target_provider = provider;
      if (baseUrl) payload.target_base_url = baseUrl;
      if (apiKeyValue) payload.target_api_key = apiKeyValue;
      if (defaultModel) payload.default_model = defaultModel;
      const res = await updateConfig(payload);
      setConfig(res.config);
      setApiKeyValue('');
      setTestResult(null);
      onConfigChanged?.();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setSaving(false);
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

  const saveLocalKey = () => {
    setApiKey(localKey);
    load();
  };

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (error && !config) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle size={40} className="text-slate-300" />
        <p className="text-sm text-slate-500">{error}</p>
        <p className="text-xs text-slate-400">请先在下方设置 Admin API Key</p>
        <div className="flex gap-2 items-center">
          <input
            type="text"
            value={localKey}
            onChange={(e) => setLocalKey(e.target.value)}
            placeholder="输入 API Key..."
            className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm font-mono w-64 focus:ring-1 focus:ring-blue-500 outline-none"
          />
          <button onClick={saveLocalKey} className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-xs font-bold">保存</button>
        </div>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      {/* Header */}
      <header className="card-panel p-4 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-800">系统设置</h2>
          <p className="text-slate-400 text-[11px] font-medium uppercase tracking-tight">上游模型配置与网关管理</p>
        </div>
        <button onClick={load} disabled={loading} className="p-1.5 hover:bg-slate-100 rounded-md text-slate-400 disabled:opacity-50">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Main config form */}
        <div className="lg:col-span-8 space-y-6">
          {/* Upstream config */}
          <section className="card-panel overflow-hidden">
            <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
              <Server size={16} className="text-slate-600" />
              <h3 className="text-xs font-bold uppercase tracking-tight text-slate-700">上游模型配置</h3>
            </div>
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Field label="Provider">
                  <input type="text" value={provider} onChange={(e) => setProvider(e.target.value)} className={inputCls} placeholder="openrouter" />
                </Field>
                <Field label="默认模型">
                  <input type="text" value={defaultModel} onChange={(e) => setDefaultModel(e.target.value)} className={inputCls} placeholder="deepseek/deepseek-v3" />
                </Field>
              </div>
              <Field label="Base URL">
                <input type="text" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} className={inputCls} placeholder="https://api.openrouter.ai/v1" />
              </Field>
              <Field label="API Key (留空不修改)">
                <div className="relative">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={apiKeyValue}
                    onChange={(e) => setApiKeyValue(e.target.value)}
                    className={cn(inputCls, 'pr-10')}
                    placeholder={config?.target.api_key_masked || '••••••••'}
                  />
                  <button onClick={() => setShowApiKey(!showApiKey)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                    {showApiKey ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </Field>

              <div className="flex gap-3 pt-2">
                <button onClick={handleSave} disabled={saving} className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-5 py-2 rounded-lg font-bold text-xs flex items-center gap-2 shadow-sm transition-colors">
                  {saving ? <RefreshCw size={12} className="animate-spin" /> : <Save size={14} />} 保存配置
                </button>
                <button onClick={handleTest} disabled={testing} className="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 px-5 py-2 rounded-lg font-bold text-xs flex items-center gap-2 shadow-sm transition-colors disabled:opacity-50">
                  {testing ? <RefreshCw size={12} className="animate-spin" /> : <Zap size={14} />} 测试连接
                </button>
              </div>

              {/* Test result */}
              {testResult && (
                <div className={cn('p-3 rounded-lg border text-xs', testResult.ok ? 'bg-emerald-50 border-emerald-100' : 'bg-red-50 border-red-100')}>
                  <div className="flex items-center gap-2 mb-1">
                    {testResult.ok ? <Check size={14} className="text-emerald-600" /> : <AlertCircle size={14} className="text-red-600" />}
                    <span className="font-bold">{testResult.ok ? '连接成功' : '连接失败'}</span>
                    {testResult.latency_ms > 0 && <span className="text-slate-400 font-mono">{testResult.latency_ms}ms</span>}
                  </div>
                  {testResult.ok && testResult.sample_models.length > 0 && (
                    <p className="text-slate-600 mt-1">可用模型: {testResult.sample_models.slice(0, 5).join(', ')}{testResult.model_count > 5 ? ` +${testResult.model_count - 5}` : ''}</p>
                  )}
                  {testResult.error && <p className="text-red-600 mt-1 break-all">{testResult.error}</p>}
                </div>
              )}
            </div>
          </section>

          {/* Current effective config (read-only) */}
          {config && (
            <section className="card-panel p-5">
              <h3 className="text-xs font-bold uppercase tracking-tight text-slate-700 mb-3">当前生效配置</h3>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-2 bg-slate-50 rounded border border-slate-100">
                  <span className="text-[9px] text-slate-400 font-bold uppercase">有效 Base URL</span>
                  <p className="font-mono text-blue-600 truncate mt-0.5">{config.effective.base_url || '(provider direct)'}</p>
                </div>
                <div className="p-2 bg-slate-50 rounded border border-slate-100">
                  <span className="text-[9px] text-slate-400 font-bold uppercase">上游模式</span>
                  <p className="font-mono text-slate-800 mt-0.5">{config.effective.upstream_mode}</p>
                </div>
                <div className="p-2 bg-slate-50 rounded border border-slate-100">
                  <span className="text-[9px] text-slate-400 font-bold uppercase">历史重写</span>
                  <p className="font-mono text-slate-800 mt-0.5">{config.history_rewrite.enabled ? config.history_rewrite.default_mode : '已禁用'}</p>
                </div>
                <div className="p-2 bg-slate-50 rounded border border-slate-100">
                  <span className="text-[9px] text-slate-400 font-bold uppercase">上下文预算</span>
                  <p className="font-mono text-slate-800 mt-0.5">{config.context_budget.enabled ? `保留 ${(config.context_budget.response_reserve_ratio * 100).toFixed(0)}%` : '已禁用'}</p>
                </div>
              </div>
            </section>
          )}
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-4 space-y-4">
          {/* Admin key */}
          <div className="card-panel p-5">
            <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">Admin API Key</h3>
            <div className="space-y-2">
              <input
                type="text"
                value={localKey}
                onChange={(e) => setLocalKey(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono focus:ring-1 focus:ring-blue-500 outline-none"
                placeholder="输入后端 API Key"
              />
              <button onClick={saveLocalKey} className="w-full bg-slate-800 text-white px-4 py-1.5 rounded-lg text-xs font-bold hover:bg-slate-700 transition-colors">
                保存至浏览器
              </button>
              <p className="text-[9px] text-slate-400">存储在 localStorage，仅用于此浏览器。</p>
            </div>
          </div>

          {/* Client access guide (collapsible) */}
          <div className="card-panel overflow-hidden">
            <button onClick={() => setShowGuide(!showGuide)} className="w-full px-5 py-3 flex items-center justify-between text-xs font-bold text-slate-700 hover:bg-slate-50 transition-colors">
              <span className="flex items-center gap-2"><Terminal size={14} /> 客户端接入指南</span>
              {showGuide ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {showGuide && (
              <div className="px-5 pb-5 space-y-3">
                <GuideBlock title="Cursor / Windsurf" code={`Base URL: http://localhost:8000/v1\nAPI Key: (your key)`} onCopy={copyText} />
                <GuideBlock title="Python / OpenAI SDK" code={`import openai\nclient = openai.OpenAI(\n  base_url="http://localhost:8000/v1",\n  api_key="your-key"\n)`} onCopy={copyText} />
                <GuideBlock title="cURL" code={`curl http://localhost:8000/v1/chat/completions \\\n  -H "Authorization: Bearer your-key" \\\n  -H "Content-Type: application/json" \\\n  -d '{"model":"default","messages":[{"role":"user","content":"hi"}]}'`} onCopy={copyText} />
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

/* ── guide block ───────────────────────────────────────────────── */

const GuideBlock = ({ title, code, onCopy }: { title: string; code: string; onCopy: (t: string) => void }) => (
  <div className="bg-slate-900 rounded-lg overflow-hidden">
    <div className="px-3 py-1.5 flex items-center justify-between border-b border-slate-800">
      <span className="text-[9px] font-bold text-slate-400 uppercase">{title}</span>
      <button onClick={() => onCopy(code)} className="text-slate-500 hover:text-white p-0.5"><Copy size={10} /></button>
    </div>
    <pre className="p-3 text-[10px] text-slate-300 font-mono leading-relaxed overflow-x-auto">{code}</pre>
  </div>
);
