import { 
  ShieldAlert, 
  Search, 
  Lock, 
  Eye, 
  History, 
  AlertTriangle,
  Fingerprint,
  Zap
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';

export const SafetyGrounding = () => {
  const { t } = useTranslation();

  /**
   * BACKEND INTEGRATION POINT:
   * Fetch active safety policies and privacy filter configurations.
   * Endpoint: GET /api/v1/safety/policies
   */
  
  /**
   * BACKEND INTEGRATION POINT:
   * Fetch recent safety grounding incidents and intervention logs.
   * Endpoint: GET /api/v1/safety/incidents
   */
  const incidents = [
    { 
      id: 'g_1', 
      type: t('grounding.hallucination'), 
      ratio: '0.45', 
      action: t('grounding.rewritten'), 
      time: '12m ago',
      evidence: 'Citation [Found in mem_45: Production IP]',
      unsupported: 'Claim: "The database is scaling automatically at 12 PM"'
    },
    // ... other incidents
  ];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <header className="flex justify-between items-center bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-800">{t('grounding.title')}</h2>
          <p className="text-slate-400 text-[11px] font-medium uppercase tracking-tight">{t('grounding.subtitle')}</p>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
          <div className="flex gap-3 mb-3">
            <div className="p-2 bg-emerald-50 text-emerald-600 rounded border border-emerald-100">
              <ShieldAlert size={18} />
            </div>
            <div>
              <div className="text-xs font-bold text-slate-800">{t('grounding.policy')}</div>
              <div className="text-[10px] text-emerald-600 font-bold uppercase">严格校验 (STRICT)</div>
            </div>
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed font-medium">
            在最终输出前对元规则索引进行事实检查。阈值：0.20 比率。
          </p>
        </div>
        
        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
          <div className="flex gap-3 mb-3">
            <div className="p-2 bg-blue-50 text-blue-600 rounded border border-blue-100">
              <Lock size={18} />
            </div>
            <div>
              <div className="text-xs font-bold text-slate-800">{t('grounding.privacy')}</div>
              <div className="text-[10px] text-blue-600 font-bold uppercase">隐私脱敏开启</div>
            </div>
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed font-medium">
            在传输至上游的过程中对敏感标识符（身份证、电话、邮箱）进行匿名化处理。
          </p>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
          <div className="flex gap-3 mb-3">
            <div className="p-2 bg-slate-50 text-slate-400 rounded border border-slate-100">
              <History size={18} />
            </div>
            <div>
              <div className="text-xs font-bold text-slate-800">{t('grounding.audit')}</div>
              <div className="text-[10px] text-slate-500 font-bold uppercase">全量原始追踪</div>
            </div>
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed font-medium">
            保留时长：30天。存储加密：AES-256。
          </p>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
        <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
          <h3 className="text-[10px] font-bold uppercase text-slate-500 tracking-widest">{t('grounding.incidents')}</h3>
          <button className="text-[10px] font-bold text-blue-600 hover:underline">{t('grounding.export')}</button>
        </div>
        <div className="divide-y divide-slate-100">
          {[
            { 
              id: 'g_1', 
              type: t('grounding.hallucination'), 
              ratio: '0.45', 
              action: t('grounding.rewritten'), 
              time: '12m ago',
              evidence: 'Citation [Found in mem_45: Production IP]',
              unsupported: 'Claim: "The database is scaling automatically at 12 PM"'
            },
            { 
              id: 'g_2', 
              type: t('grounding.pii'), 
              ratio: 'N/A', 
              action: t('grounding.masked'), 
              time: '1h ago',
              evidence: 'Masked Pattern: [IP_ADDRESS]',
              unsupported: 'N/A'
            },
            { 
              id: 'g_3', 
              type: t('grounding.unverified'), 
              ratio: '0.12', 
              action: t('grounding.note'), 
              time: '3h ago',
              evidence: 'No direct Meta-rule (元规则) match found.',
              unsupported: 'Claim: "The project will launch next Tuesday"'
            },
          ].map(incident => (
            <div key={incident.id} className="p-4 flex flex-col gap-3 hover:bg-slate-50 transition-colors">
              <div className="flex items-center gap-4">
                <div className="p-1.5 bg-slate-100 rounded text-slate-400">
                  <AlertTriangle size={14} className={cn(incident.action === t('grounding.rewritten') ? "text-amber-500" : "text-blue-500")} />
                </div>
                <div className="flex-1">
                  <div className="text-[11px] font-bold text-slate-700">{incident.type}</div>
                  <div className="text-[9px] text-slate-400 uppercase font-bold tracking-wider">Ratio: {incident.ratio}</div>
                </div>
                <div className="text-right">
                  <div className={cn(
                    "text-[10px] font-bold uppercase tracking-tight",
                    incident.action === t('grounding.rewritten') ? "text-amber-600" : "text-emerald-600"
                  )}>{incident.action}</div>
                  <div className="text-[9px] text-slate-400 font-mono font-medium">{incident.time}</div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-10 border-l border-slate-100 ml-3">
                 <div className="p-2 bg-slate-50 rounded border border-slate-100">
                    <div className="text-[8px] font-bold text-slate-400 uppercase mb-1 tracking-widest">Evidence / Citation</div>
                    <div className="text-[10px] text-slate-600 font-medium italic">{incident.evidence}</div>
                 </div>
                 <div className="p-2 bg-slate-50 rounded border border-slate-100">
                    <div className="text-[8px] font-bold text-slate-400 uppercase mb-1 tracking-widest">Unsupported Claims</div>
                    <div className="text-[10px] text-rose-600 font-medium italic">{incident.unsupported}</div>
                 </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
         <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm overflow-hidden">
            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Grounding Rewrite Comparison (Sample)</h4>
            <div className="space-y-4">
               <div>
                  <div className="text-[9px] font-bold text-slate-400 uppercase mb-2">Original Model Output</div>
                  <div className="p-3 bg-slate-50 text-slate-400 border border-slate-100 rounded text-[10px] font-sans line-through">
                    The server deployment is highly optimized and occurs at 12 PM every day without fail.
                  </div>
               </div>
               <div>
                  <div className="text-[9px] font-bold text-slate-800 uppercase mb-2">Gateway Intervened Output</div>
                  <div className="p-3 bg-blue-50 text-blue-800 border border-blue-100 rounded text-[10px] font-sans font-medium italic">
                    The server deployment procedure is currently undergoing optimization. (Note: specific timing is unverified).
                  </div>
               </div>
            </div>
         </div>

         <div className="bg-[#0F172A] text-white p-6 rounded-lg shadow-xl flex flex-col justify-between">
            <div>
               <div className="flex items-center gap-2 mb-4">
                  <Fingerprint className="text-blue-400" size={24} />
                  <h4 className="text-xs font-bold uppercase tracking-[0.2em]">Safety Protocol: Degrade Mode</h4>
               </div>
               <p className="text-[11px] text-slate-400 leading-relaxed font-medium">
                 当接地比例 (unsupported_ratio) 超过阈值时，Gateway 将自动触发回落至“保守模式”，拒绝猜测，仅输出已验证的事实条目。
               </p>
            </div>
            <div className="mt-6 flex items-center justify-between">
               <div className="text-[10px] font-bold uppercase tracking-tight text-blue-300">Auto-Degrade Status:</div>
               <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_#10b981]"></div>
                  <span className="text-[11px] font-mono font-bold text-emerald-400 uppercase tracking-widest text-xs">Standby</span>
               </div>
            </div>
         </div>
      </section>
    </motion.div>
  );
};
