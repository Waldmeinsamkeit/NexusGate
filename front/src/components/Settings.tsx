import { useTranslation } from 'react-i18next';
import { motion } from 'motion/react';
import { 
  Shield, 
  Key, 
  Settings as SettingsIcon, 
  Save, 
  Database, 
  FileCode,
  AlertTriangle,
  FolderOpen
} from 'lucide-react';
import { cn } from '../lib/utils';

export const Settings = () => {
  const { t } = useTranslation();

  /**
   * BACKEND INTEGRATION POINT:
   * Fetch current system environment variables and configuration settings.
   * Endpoint: GET /api/v1/system/config
   */
  
  /**
   * BACKEND INTEGRATION POINT:
   * Save updated configuration and trigger a system reload/restart.
   * Endpoint: POST /api/v1/system/config/reload
   * Payload: { env: string, settings: Object }
   */

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <header className="flex justify-between items-center bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-800">{t('nav.settings')}</h2>
          <p className="text-slate-400 text-[11px] font-medium uppercase tracking-tight">Core System Config & Identity Management</p>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        <div className="md:col-span-8 space-y-6">
          <section className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
            <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
              <FileCode size={16} className="text-slate-600" />
              <h3 className="text-xs font-bold uppercase tracking-tight text-slate-700">Environment Variables (.env)</h3>
            </div>
            <div className="p-5">
              <div className="bg-slate-900 rounded-lg p-4 mb-4">
                <textarea 
                  rows={8}
                  className="w-full bg-transparent border-0 text-blue-300 font-mono text-xs focus:ring-0 outline-none resize-none leading-relaxed"
                  defaultValue={`# NexusGate Core Env
TARGET_PROVIDER=openrouter
TARGET_BASE_URL=https://api.openrouter.ai/v1
TARGET_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx
DEFAULT_MODEL=deepseek/deepseek-v3

# Memory Configuration
MEMORY_PATH=./data/vectors
SHARD_COUNT=14
PII_MASKING=true`}
                />
              </div>
              <div className="flex items-center gap-4 text-amber-600 bg-amber-50 p-3 rounded border border-amber-100 text-[10px] font-bold uppercase mb-4">
                 <AlertTriangle size={14} className="shrink-0" />
                 <span>警告：直接修改 .env 变量需要重启 NexusGate 内核服务方可生效。</span>
              </div>
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-bold text-xs flex items-center gap-2 shadow-sm transition-all">
                <Save size={14} />
                保存配置并排队重启
              </button>
            </div>
          </section>

          <section className="bg-white border border-slate-200 rounded-lg shadow-sm p-5">
             <h3 className="text-xs font-bold uppercase tracking-tight text-slate-700 mb-4 flex items-center gap-2">
                <FolderOpen size={16} className="text-slate-600" />
                存储路径设置
             </h3>
             <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                   <label className="text-[10px] font-bold text-slate-400 uppercase">向量索引路径</label>
                   <input type="text" className="w-full bg-slate-50 border border-slate-200 rounded px-3 py-1.5 text-xs" defaultValue="./data/vectors" />
                </div>
                <div className="space-y-1.5">
                   <label className="text-[10px] font-bold text-slate-400 uppercase">审计日志级别</label>
                   <select className="w-full bg-slate-50 border border-slate-200 rounded px-3 py-1.5 text-xs">
                      <option>FULL_RAW_TRACING</option>
                      <option>METADATA_ONLY</option>
                      <option>DISABLED</option>
                   </select>
                </div>
             </div>
          </section>
        </div>

        <div className="md:col-span-4 space-y-4">
           <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
              <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                 <Shield size={14} className="text-emerald-600" />
                 安全令牌
              </h3>
              <div className="space-y-4">
                 <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                    <div className="text-[9px] font-bold text-slate-400 uppercase mb-1">管理员 API Key</div>
                    <div className="flex items-center justify-between">
                       <span className="font-mono text-xs">nk_adm_********92u</span>
                       <button className="text-[10px] text-blue-600 font-bold hover:underline">更新</button>
                    </div>
                 </div>
                 <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                    <div className="text-[9px] font-bold text-slate-400 uppercase mb-1">主接入令牌</div>
                    <div className="flex items-center justify-between">
                       <span className="font-mono text-xs">nk_acc_********v4x</span>
                       <button className="text-[10px] text-blue-600 font-bold hover:underline">复制</button>
                    </div>
                 </div>
              </div>
           </div>

           <div className="p-5 bg-blue-50 border border-blue-100 rounded-lg">
              <h4 className="text-[10px] font-bold text-blue-600 uppercase tracking-widest mb-2">DEBUG MODE</h4>
              <p className="text-[11px] text-blue-800 leading-relaxed font-medium mb-3">
                 启用调试模式将输出所有 Prompt 的重写逻辑到标准控制台。
              </p>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" defaultChecked />
                <div className="w-8 h-4 bg-slate-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
           </div>
        </div>
      </div>
    </motion.div>
  );
};
