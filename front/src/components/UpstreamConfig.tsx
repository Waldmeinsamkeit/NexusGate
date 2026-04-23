import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Server, 
  Settings2, 
  Plus, 
  Globe, 
  Key, 
  Box, 
  Activity, 
  ShieldAlert, 
  ArrowRight,
  TestTube,
  Trash2,
  AlertCircle
} from 'lucide-react';
import { mockUpstreams } from '../services/mockData';
import { cn } from '../lib/utils';
import { motion } from 'motion/react';

const UpstreamCard = ({ config }: { config: any, key?: React.Key }) => {
  const { t } = useTranslation();
  return (
  <div className="bg-white border border-slate-200 rounded-lg shadow-sm group hover:border-blue-400 transition-all overflow-hidden flex flex-col">
    <div className="p-4 flex-1">
      <div className="flex justify-between items-start mb-4">
        <div className="flex gap-3">
          <div className={cn(
            "p-2 rounded-lg border",
            config.isEnabled ? "bg-blue-50 text-blue-600 border-blue-100" : "bg-slate-50 text-slate-400 border-slate-100"
          )}>
            <Server size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <h4 className="font-bold text-xs text-slate-800">{config.name}</h4>
              {config.isDefault && (
                <span className="px-1 py-0.5 bg-blue-600 text-white text-[8px] font-bold uppercase rounded tracking-wider">{t('upstreams.primary')}</span>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-[9px] text-slate-500 font-bold uppercase tracking-tight">
              <span>{config.provider}</span>
              <span className="w-0.5 h-0.5 bg-slate-300 rounded-full" />
              <span>{config.type}</span>
            </div>
          </div>
        </div>
        <button className="p-1.5 hover:bg-slate-50 rounded text-slate-400 hover:text-slate-700 transition-colors">
          <Settings2 size={14} />
        </button>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2 p-1.5 rounded bg-slate-50 border border-slate-100">
          <Globe size={12} className="text-slate-400 shrink-0" />
          <div className="text-[10px] font-mono text-blue-600 truncate flex-1">{config.baseUrl}</div>
        </div>
        <div className="flex items-center gap-2 p-1.5 rounded bg-slate-50 border border-slate-100">
          <Key size={12} className="text-slate-400 shrink-0" />
          <div className="text-[10px] font-mono text-slate-500 truncate flex-1">{config.apiKey}</div>
        </div>
        <div className="flex items-center gap-2 p-1.5 rounded bg-slate-50 border border-slate-100">
          <Box size={12} className="text-slate-400 shrink-0" />
          <div className="text-[10px] font-mono text-slate-700 truncate flex-1">{config.defaultModel}</div>
        </div>
      </div>
    </div>

    <div className="px-4 py-2 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <button 
          onClick={() => {
            /**
             * BACKEND INTEGRATION POINT:
             * Test connection to the upstream provider and check latency.
             * Endpoint: POST /api/v1/upstreams/:id/test
             */
            alert(`正在测试连接至 ${config.name}...`);
          }}
          className="p-1 hover:bg-white rounded text-slate-400 hover:text-blue-600 transition-colors" 
          title="Test Connection"
        >
          <TestTube size={14} />
        </button>
        <div className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider">
          <div className={cn("w-1 h-1 rounded-full", config.isEnabled ? "bg-emerald-500 shadow-[0_0_4px_#10b981]" : "bg-slate-300")} />
          <span className={config.isEnabled ? "text-emerald-600" : "text-slate-400"}>
            {config.latency ? `${config.latency}ms ${t('common.latency')}` : t('common.offline')}
          </span>
        </div>
      </div>
      <label className="relative inline-flex items-center cursor-pointer">
        <input type="checkbox" className="sr-only peer" defaultChecked={config.isEnabled} />
        <div className="w-7 h-4 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-blue-600"></div>
      </label>
    </div>
  </div>
  );
};

export const UpstreamConfigView = () => {
  const { t } = useTranslation();

  /**
   * BACKEND INTEGRATION POINT:
   * Fetch all configured upstream targets (Gateways and Legacy APIs).
   * Endpoint: GET /api/v1/upstreams
   */
  const upstreams = mockUpstreams; // Replace with state from API

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <header className="flex justify-between items-center bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-800">{t('upstreams.title')}</h2>
          <p className="text-slate-400 text-[11px] font-medium uppercase tracking-tight">{t('upstreams.subtitle')}</p>
        </div>
        <div className="flex gap-2">
          <button className="bg-white hover:bg-slate-50 text-slate-700 px-4 py-2 rounded-lg font-bold text-xs border border-slate-200 transition-all shadow-sm uppercase tracking-wider">
            {t('upstreams.import')}
          </button>
          <button className="bg-[#29c095] hover:bg-[#22a37e] text-white px-4 py-2 rounded-lg font-bold text-xs flex items-center gap-2 transition-all shadow-sm uppercase tracking-wider">
            <Plus size={14} />
            {t('upstreams.addTarget')}
          </button>
        </div>
      </header>

      <div className="flex items-center gap-4 p-3 bg-amber-50 border border-amber-100 rounded-lg text-amber-700">
        <AlertCircle size={16} className="shrink-0" />
        <p className="text-[11px] font-bold uppercase tracking-tight">
          检测到旧版 <code className="bg-amber-100 px-1 rounded">LLMAPI_*</code> 配置。建议：迁移至 <code className="bg-amber-100 px-1 rounded">TARGET_*</code> 标准。
        </p>
        <button className="ml-auto text-[10px] font-bold uppercase tracking-widest underline">自动迁移</button>
      </div>

      <div className="space-y-6">
        <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-1">{t('upstreams.activeTargets')}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {mockUpstreams.filter(u => u.type === 'TARGET').map(config => (
            <UpstreamCard key={config.id} config={config} />
          ))}
        </div>
      </div>

      <hr className="border-slate-100 my-8" />

      <div className="space-y-4 pb-8">
        <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-1">{t('upstreams.legacy')}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {mockUpstreams.filter(u => u.type === 'LLMAPI_LEGACY').map(config => (
            <UpstreamCard key={config.id} config={config} />
          ))}
        </div>
      </div>
    </motion.div>
  );
};
