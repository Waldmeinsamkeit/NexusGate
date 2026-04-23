import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Activity, 
  Search, 
  ChevronRight, 
  Clock, 
  Database, 
  Zap, 
  ArrowRightLeft, 
  Scissors, 
  Edit3, 
  AlertCircle,
  FileText,
  GitBranch,
  ShieldCheck,
  Code
} from 'lucide-react';
import { mockTraces } from '../services/mockData';
import { cn } from '../lib/utils';
import { RequestTrace } from '../types';

export const RequestTracing = () => {
  const { t } = useTranslation();
  
  /**
   * BACKEND INTEGRATION POINT:
   * Fetch the list of historical or real-time request traces.
   * Endpoint: GET /api/v1/traces/stream or /api/v1/traces/list
   * Query Params: sessionId, model, search
   */
  const traces = mockTraces; // Replace with actual API data source

  const [selectedTrace, setSelectedTrace] = useState<RequestTrace | null>(traces[0]);
  const [search, setSearch] = useState('');

  const filteredTraces = traces.filter(t => 
    t.id.toLowerCase().includes(search.toLowerCase()) || 
    t.sessionId.toLowerCase().includes(search.toLowerCase()) ||
    t.model.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col h-[calc(100vh-80px)] space-y-4"
    >
      <header className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm flex justify-between items-center shrink-0">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-800">请求追踪</h2>
          <p className="text-slate-400 text-[10px] font-bold uppercase tracking-widest italic">NexusGate 可运营性审计中心</p>
        </div>
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
          <input 
            type="text" 
            placeholder="搜索 Trace ID 或 Session..."
            className="w-full bg-slate-50 border border-slate-200 rounded-lg py-1.5 pl-9 pr-4 text-xs focus:ring-1 focus:ring-blue-500 outline-none"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </header>

      <div className="flex-1 min-h-0 flex gap-4">
        {/* List Side */}
        <section className="w-1/3 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500">实时请求流</h3>
            <span className="text-[9px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded font-bold">LATEST</span>
          </div>
          <div className="flex-1 overflow-y-auto divide-y divide-slate-50 custom-scrollbar">
            {filteredTraces.map((trace) => (
              <button
                key={trace.id}
                onClick={() => setSelectedTrace(trace)}
                className={cn(
                  "w-full text-left p-4 transition-all hover:bg-slate-50 relative group",
                  selectedTrace?.id === trace.id ? "bg-blue-50/50" : ""
                )}
              >
                {selectedTrace?.id === trace.id && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-600"></div>
                )}
                <div className="flex justify-between items-start mb-1.5">
                  <div className="font-mono text-[10px] font-bold text-slate-400">#{trace.id}</div>
                  <div className={cn(
                    "px-1.5 py-0.5 rounded text-[9px] font-bold uppercase",
                    trace.status === 'success' ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"
                  )}>
                    {trace.status}
                  </div>
                </div>
                <div className="text-xs font-bold text-slate-700 truncate mb-2">{trace.provider} / {trace.model}</div>
                <div className="flex items-center gap-3 text-[10px] text-slate-400 font-medium">
                  <span className="flex items-center gap-1"><Clock size={10} /> {trace.latency}ms</span>
                  {trace.fallback && <span className="flex items-center gap-1 text-amber-500 font-bold"><Zap size={10} /> FALLBACK</span>}
                  {trace.rewrite && <span className="flex items-center gap-1 text-blue-500 font-bold"><Edit3 size={10} /> REWRITE</span>}
                </div>
              </button>
            ))}
          </div>
        </section>

        {/* Details Side */}
        <section className="flex-1 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col">
          {selectedTrace ? (
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-[#0F172A] text-white rounded-lg">
                    <Activity size={18} />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-800">请求运行审计回放</h3>
                    <p className="text-[10px] text-slate-400 font-mono">Session ID: {selectedTrace.sessionId}</p>
                  </div>
                </div>
                <div className="flex gap-4">
                   <div className="text-center">
                      <div className="text-[9px] font-bold text-slate-400 uppercase">Trim</div>
                      <div className="text-xs font-mono font-bold text-slate-700">-{selectedTrace.trim}t</div>
                   </div>
                   <div className="text-center">
                      <div className="text-[9px] font-bold text-slate-400 uppercase">Unsupported</div>
                      <div className="text-xs font-mono font-bold text-rose-500">{(selectedTrace.unsupported_ratio * 100).toFixed(0)}%</div>
                   </div>
                </div>
              </div>

              <div className="p-6 space-y-6">
                {/* 1. Original Input */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                    <FileText size={12} />
                    Original Input (原始输入)
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-100 rounded-lg text-xs italic text-slate-600 leading-relaxed">
                    "{selectedTrace.details.originalInput}"
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  {/* 2. Route Decision */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                      <GitBranch size={12} className="text-blue-500" />
                      Route Decision (路由决策)
                    </div>
                    <div className="p-3 bg-blue-50/30 border border-blue-100 rounded-lg text-xs font-bold text-blue-800">
                      {selectedTrace.details.routeDecision}
                    </div>
                  </div>
                  {/* 3. Provider/Model */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                      <Database size={12} className="text-emerald-500" />
                      Selected Provider / Model
                    </div>
                    <div className="p-3 bg-emerald-50/30 border border-emerald-100 rounded-lg text-xs font-bold text-emerald-800">
                      {selectedTrace.details.selectedProviderModel}
                    </div>
                  </div>
                </div>

                {/* 4. Fallback Chain */}
                <div className="space-y-2">
                   <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                    <ArrowRightLeft size={12} className="text-amber-500" />
                    Fallback Chain (备选链路)
                  </div>
                  <div className="flex items-center gap-2">
                    {selectedTrace.details.fallbackChain.length > 0 ? (
                      selectedTrace.details.fallbackChain.map((f, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <span className="px-2 py-1 bg-slate-100 text-slate-600 rounded text-[10px] font-bold">{f}</span>
                          <ChevronRight size={12} className="text-slate-300" />
                        </div>
                      ))
                    ) : (
                      <span className="text-[10px] text-slate-400 font-bold italic">NONE (PRIMARY SUCCESS)</span>
                    )}
                    <span className="px-2 py-1 bg-blue-600 text-white rounded text-[10px] font-bold">{selectedTrace.model}</span>
                  </div>
                </div>

                {/* 5. Memory Hubs */}
                <div className="grid grid-cols-2 gap-6">
                   <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                      <Database size={12} className="text-purple-500" />
                      Memory Hit Summary
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {selectedTrace.details.memoryHitSummary.map(m => (
                        <span key={m} className="px-2 py-1 bg-purple-50 text-purple-600 border border-purple-100 rounded text-[10px] font-bold">
                          {m}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                      <Scissors size={12} className="text-rose-500" />
                      Trim Report (裁剪报告)
                    </div>
                    <div className="text-xs text-slate-500 leading-relaxed border-l-2 border-rose-100 pl-3 italic">
                      {selectedTrace.details.trimReport}
                    </div>
                  </div>
                </div>

                {/* 6. Grounding */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest text-emerald-600">
                    <ShieldCheck size={12} />
                    Grounding Summary (落地验证总结)
                  </div>
                  <div className="p-3 bg-emerald-50/20 border border-emerald-100 rounded-lg text-xs text-emerald-800 flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                    {selectedTrace.details.groundingSummary}
                  </div>
                </div>

                {/* 7. Rewrite Diff */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest text-blue-600">
                    <Code size={12} />
                    Rewrite Diff (重写前后差异)
                  </div>
                  <pre className="p-3 bg-[#1e293b] text-blue-300 font-mono text-[10px] rounded-lg overflow-x-auto whitespace-pre-wrap">
                    {selectedTrace.details.rewriteDiff}
                  </pre>
                </div>

                {/* 8. Final Response */}
                <div className="space-y-2 pt-4 border-t border-slate-100">
                  <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                    <Zap size={12} className="text-amber-500" />
                    Final Response (中：最终网关响应)
                  </div>
                  <div className="p-4 bg-slate-900 text-slate-100 rounded-xl text-xs leading-relaxed font-medium shadow-xl">
                    {selectedTrace.details.finalResponse}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-12 space-y-6">
               <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center text-slate-200">
                  <Activity size={32} />
               </div>
               <div>
                  <h4 className="text-sm font-bold text-slate-800 mb-2">等待选中 Trace 条目</h4>
                  <p className="text-xs text-slate-400 max-w-xs mx-auto italic">请在左侧列表中选择一个请求，以回放其具体的路由决策与内存生命周期数据。</p>
               </div>
            </div>
          )}
        </section>
      </div>
    </motion.div>
  );
};
