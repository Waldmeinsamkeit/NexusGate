import { useTranslation } from 'react-i18next';
import { motion } from 'motion/react';
import { 
  Scissors, 
  Layers, 
  Brain, 
  ArrowRight, 
  CheckCircle2, 
  AlertCircle,
  FileJson,
  Hash
} from 'lucide-react';
import { cn } from '../lib/utils';

export const MemoryPackPreview = () => {
  const { t } = useTranslation();

  /**
   * BACKEND INTEGRATION POINT:
   * Fetch the most recent or a specific token trimming report.
   * Endpoint: GET /api/v1/memory-packs/report/:requestId
   */
  const trimReport = {
    beforeTokens: 145200,
    afterTokens: 126000,
    limit: 128000,
    preserved: [
      { id: 'm_1', title: 'System_Persona', layer: 'L0', tokens: 1200 },
      { id: 'm_2', title: 'User_Security_Context', layer: 'constraints', tokens: 800 },
      { id: 'm_3', title: 'Project_Alpha_Specs', layer: 'facts', tokens: 124000 },
    ],
    clipped: [
      { id: 'm_4', title: 'Old_Session_Context', layer: 'continuity', tokens: 15000 },
      { id: 'm_5', title: 'Generic_Trivia', layer: 'facts', tokens: 4200 },
    ]
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <header className="flex justify-between items-center bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-800">{t('memoryPack.title')}</h2>
          <p className="text-slate-400 text-[11px] font-medium uppercase tracking-tight">{t('memoryPack.subtitle')}</p>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <section className="bg-[#0F172A] text-white rounded-lg overflow-hidden border border-slate-800">
            <div className="px-4 py-3 bg-slate-800/50 border-b border-slate-700 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <FileJson size={16} className="text-blue-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider">{t('memoryPack.assembled')}</h3>
              </div>
              <div className="text-[10px] font-mono text-slate-400 uppercase">Provider: DeepSeek-V3 (OpenRouter)</div>
            </div>
            <div className="p-4 overflow-x-auto">
              <pre className="text-xs font-mono text-blue-300 leading-relaxed">
                {`{
  "system": "You are NexusGate Assistant...",
  "memory_pack": {
    "l0": [...],
    "constraints": [...],
    "facts": [...],
    "continuity": [...]
  },
  "current_query": "Explain the project alpha architecture..."
}`}
              </pre>
            </div>
          </section>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
             <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm border-l-4 border-l-emerald-500">
                <div className="flex items-center gap-2 mb-3">
                   <div className="p-1.5 bg-emerald-50 text-emerald-600 rounded">
                      <CheckCircle2 size={16} />
                   </div>
                   <h4 className="text-xs font-bold text-slate-800 uppercase tracking-tight">{t('memoryPack.preserved')}</h4>
                </div>
                <div className="space-y-2">
                   {trimReport.preserved.map(item => (
                     <div key={item.id} className="flex justify-between items-center text-[11px] py-1 border-b border-slate-50 last:border-0">
                        <span className="font-medium text-slate-600 italic">[{t(`layers.${item.layer}`)}] {item.title}</span>
                        <span className="font-mono text-slate-400">{item.tokens} tkn</span>
                     </div>
                   ))}
                </div>
             </div>

             <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm border-l-4 border-l-amber-500">
                <div className="flex items-center gap-2 mb-3">
                   <div className="p-1.5 bg-amber-50 text-amber-600 rounded">
                      <Scissors size={16} />
                   </div>
                   <h4 className="text-xs font-bold text-slate-800 uppercase tracking-tight">{t('memoryPack.clipped')}</h4>
                </div>
                <div className="space-y-2">
                   {trimReport.clipped.map(item => (
                     <div key={item.id} className="flex justify-between items-center text-[11px] py-1 border-b border-slate-50 last:border-0">
                        <span className="font-medium text-amber-600/70 line-through italic">[{t(`layers.${item.layer}`)}] {item.title}</span>
                        <span className="font-mono text-slate-400">{item.tokens} tkn</span>
                     </div>
                   ))}
                </div>
             </div>
          </div>
        </div>

        <div className="space-y-4">
           <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
              <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-6">{t('memoryPack.trimReport')}</h3>
              
              <div className="space-y-8">
                 <div className="relative">
                    <div className="flex justify-between text-[11px] mb-2">
                       <span className="font-bold text-slate-600">{t('memoryPack.before')}</span>
                       <span className="font-mono text-slate-400">{trimReport.beforeTokens.toLocaleString()}</span>
                    </div>
                    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                       <div className="h-full bg-slate-300 w-full"></div>
                    </div>
                 </div>

                 <div className="flex justify-center py-2">
                    <ArrowRight className="text-blue-500 animate-pulse" size={20} />
                 </div>

                 <div className="relative">
                    <div className="flex justify-between text-[11px] mb-2">
                       <span className="font-bold text-slate-800">{t('memoryPack.after')}</span>
                       <span className="font-mono text-blue-600">{trimReport.afterTokens.toLocaleString()}</span>
                    </div>
                    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                       <div 
                         className="h-full bg-blue-600 shadow-[0_0_8px_#2563eb]" 
                         style={{ width: `${(trimReport.afterTokens / trimReport.beforeTokens) * 100}%` }}
                       ></div>
                    </div>
                    <div 
                       className="absolute top-8 left-0 text-[9px] font-bold text-slate-400 uppercase italic"
                    >
                       Limit: {trimReport.limit.toLocaleString()}
                    </div>
                 </div>

                 <div className="mt-12 pt-6 border-t border-slate-100">
                    <div className="flex items-center gap-3 text-emerald-600">
                       <Hash size={16} />
                       <div>
                          <div className="text-[10px] font-bold uppercase tracking-tight">{t('memoryPack.reductionEfficiency')}</div>
                          <div className="text-lg font-mono font-bold">13.2%</div>
                       </div>
                    </div>
                 </div>
              </div>
           </div>

           <div className="p-4 bg-indigo-600 text-white rounded-lg shadow-lg">
              <h4 className="text-[10px] font-bold uppercase tracking-widest opacity-80 mb-2">{t('memoryPack.trimmingLogic')}</h4>
              <p className="text-[11px] font-medium leading-relaxed italic">
                {t('memoryPack.trimmingDescription')}
              </p>
           </div>
        </div>
      </div>
    </motion.div>
  );
};
