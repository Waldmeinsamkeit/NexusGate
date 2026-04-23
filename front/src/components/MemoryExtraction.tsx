import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'motion/react';
import { 
  FileText, 
  Sparkles, 
  ChevronRight, 
  CheckCircle2, 
  AlertCircle,
  Database,
  Search,
  ArrowRight,
  Plus,
  Trash2,
  Save,
  Hash,
  History,
  GitMerge,
  Archive,
  Ban,
  Filter,
  CheckSquare,
  Square,
  MoreVertical,
  Layers,
  Zap
} from 'lucide-react';
import { cn } from '../lib/utils';
import { mockMemories } from '../services/mockData';

export const MemoryExtraction = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'extract' | 'manage'>('extract');
  const [sourceText, setSourceText] = useState('');
  const [isExtracting, setIsExtracting] = useState(false);
  
  // Management state
  const [search, setSearch] = useState('');
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [filterLayer, setFilterLayer] = useState<string>('all');

  const [candidates, setCandidates] = useState([
    { id: 'c1', title: '服务器配置变更', content: '备份服务器 IP 已变更为 10.0.0.50', layer: 'facts', confidence: 0.92, status: 'pending' },
    { id: 'c2', title: '用户偏好语调', content: '用户不喜欢过于生硬的正式用语，偏好技术俚语风格。', layer: 'constraints', confidence: 0.88, status: 'pending' },
  ]);

  const filteredMemories = useMemo(() => {
    return mockMemories.filter(m => {
      const matchesSearch = m.title.toLowerCase().includes(search.toLowerCase()) || 
                          m.content.toLowerCase().includes(search.toLowerCase());
      const matchesLayer = filterLayer === 'all' || m.layer === filterLayer;
      return matchesSearch && matchesLayer;
    });
  }, [search, filterLayer]);

  const handleExtract = () => {
    /**
     * BACKEND INTEGRATION POINT:
     * Trigger the AI memory extraction engine.
     * Endpoint: POST /api/v1/extract
     * Payload: { sourceText: string }
     * Returns: Array of candidate memory objects
     */
    setIsExtracting(true);
    setTimeout(() => setIsExtracting(false), 1500);
  };

  const toggleSelection = (id: string) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col h-[calc(100vh-80px)] space-y-4"
    >
      {/* Header with Navigation */}
      <header className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm flex flex-col md:flex-row justify-between items-center gap-4 shrink-0">
        <div className="flex items-center gap-4">
          <div className="bg-blue-600 p-2.5 rounded-lg text-white shadow-lg shadow-blue-500/20">
            <Zap size={20} />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-800">{t('extraction.title')}</h2>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{t('extraction.subtitle')}</span>
              <span className="w-1 h-1 bg-slate-300 rounded-full"></span>
              <span className="text-[10px] text-blue-500 font-bold uppercase tracking-widest italic">Stable Kernel v1.2</span>
            </div>
          </div>
        </div>

        <div className="flex bg-slate-100 p-1 rounded-lg border border-slate-200">
           <button 
             onClick={() => setActiveTab('extract')}
             className={cn(
               "px-4 py-1.5 text-xs font-bold rounded-md transition-all flex items-center gap-2",
               activeTab === 'extract' ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
             )}
           >
             <Sparkles size={14} />
             实时提取
           </button>
           <button 
             onClick={() => setActiveTab('manage')}
             className={cn(
               "px-4 py-1.5 text-xs font-bold rounded-md transition-all flex items-center gap-2",
               activeTab === 'manage' ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
             )}
           >
             <Layers size={14} />
             工作台管理
           </button>
        </div>
      </header>

      <div className="flex-1 min-h-0">
        <AnimatePresence mode="wait">
          {activeTab === 'extract' ? (
            <motion.div 
              key="extract"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-full"
            >
              {/* Left: Input */}
              <div className="lg:col-span-5 flex flex-col gap-4 h-full">
                <section className="flex-1 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col">
                  <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                    <div className="flex items-center gap-2 text-slate-600">
                      <FileText size={14} />
                      <h3 className="text-[10px] font-bold uppercase tracking-widest">{t('extraction.source')}</h3>
                    </div>
                    <div className="text-[9px] font-bold text-slate-400 font-mono italic">CHARS: {sourceText.length}</div>
                  </div>
                  <div className="flex-1 p-4">
                    <textarea 
                      value={sourceText}
                      onChange={(e) => setSourceText(e.target.value)}
                      className="w-full h-full p-4 bg-slate-50/50 rounded-lg border border-slate-100 text-xs font-mono resize-none focus:ring-1 focus:ring-blue-500 outline-none scrollbar-hide"
                      placeholder={t('extraction.sourcePlaceholder')}
                    />
                  </div>
                  <div className="p-4 bg-white border-t border-slate-50">
                    <button 
                      onClick={handleExtract}
                      disabled={!sourceText || isExtracting}
                      className={cn(
                        "w-full py-2.5 rounded-lg font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-md",
                        sourceText && !isExtracting ? "bg-blue-600 hover:bg-blue-700 text-white" : "bg-slate-100 text-slate-400 cursor-not-allowed shadow-none"
                      )}
                    >
                      {isExtracting ? (
                        <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      ) : (
                        <Sparkles size={14} />
                      )}
                      {isExtracting ? t('extraction.analyzing') : t('extraction.run')}
                    </button>
                  </div>
                </section>
              </div>

              {/* Right: Candidates & Queue */}
              <div className="lg:col-span-7 grid grid-cols-1 md:grid-cols-2 gap-4 h-full">
                <section className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col">
                  <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 flex items-center gap-2">
                    <Sparkles size={14} className="text-blue-500" />
                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-600">{t('extraction.candidates')}</h3>
                  </div>
                  <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                    {candidates.map(candidate => (
                      <div key={candidate.id} className="group border border-slate-100 bg-white rounded-lg p-3 hover:border-blue-200 hover:bg-blue-50/10 transition-all relative">
                        <div className="flex justify-between items-start mb-2">
                           <div className="px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded text-[9px] font-bold uppercase tracking-tighter">
                              {t(`layers.${candidate.layer}`)}
                           </div>
                           <div className="text-[10px] font-mono text-emerald-500 font-bold">{(candidate.confidence * 100).toFixed(0)}% {t('extraction.match')}</div>
                        </div>
                        <h4 className="text-xs font-bold text-slate-800 mb-1">{candidate.title}</h4>
                        <p className="text-[11px] text-slate-500 italic mb-3">"{candidate.content}"</p>
                        <div className="flex justify-end gap-2">
                           <button className="p-1.5 hover:bg-slate-100 rounded text-slate-400 hover:text-rose-500 transition-colors">
                              <Trash2 size={12} />
                           </button>
                           <button className="flex items-center gap-1.5 px-3 py-1 bg-white border border-slate-200 text-slate-600 rounded text-[10px] font-bold shadow-sm hover:border-blue-300">
                              <Plus size={10} />
                              暂存
                           </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col">
                  <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 flex items-center gap-2">
                    <CheckCircle2 size={14} className="text-emerald-500" />
                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-600">{t('extraction.pending')}</h3>
                  </div>
                  <div className="flex-1 p-4 overflow-y-auto space-y-3">
                     <div className="p-3 bg-emerald-50/50 border border-emerald-100 rounded-lg flex items-center justify-between group">
                        <div className="min-w-0">
                           <div className="text-xs font-bold text-emerald-800 truncate">数据库同步规则升级</div>
                           <div className="text-[10px] text-emerald-600 font-mono italic">FACT -{">"} CORE KNOWLEDGE</div>
                        </div>
                        <Trash2 size={14} className="text-emerald-400 opacity-0 group-hover:opacity-100 cursor-pointer" />
                     </div>
                  </div>
                  <div className="p-4 bg-slate-50 border-t border-slate-100 space-y-3">
                     <button 
                       onClick={() => {
                         /**
                          * BACKEND INTEGRATION POINT:
                          * Commit the pending memories to the Nexus Core knowledge graph.
                          * Endpoint: POST /api/v1/memories/commit
                          * Payload: { memories: Array<PendingMemory> }
                          */
                         alert('已提交至 Nexus 核心存储库');
                       }}
                       className="w-full bg-[#0F172A] hover:bg-slate-800 text-white py-2.5 rounded-lg font-bold text-xs flex items-center justify-center gap-2 shadow-lg transition-all group"
                     >
                        <Hash size={14} className="text-blue-400 group-hover:rotate-12 transition-transform" />
                        {t('extraction.commit')}
                     </button>
                  </div>
                </section>
              </div>
            </motion.div>
          ) : (
            <motion.div 
              key="manage"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="flex flex-col h-full gap-4"
            >
              {/* Workbench Management UI */}
              <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm space-y-4 shrink-0">
                <div className="flex flex-col md:flex-row gap-4 items-center">
                  <div className="relative flex-1 w-full">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
                    <input 
                      type="text" 
                      placeholder={t('extraction.workbench.search') + "记忆、内容或来源..."}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 pl-9 pr-4 text-sm focus:ring-1 focus:ring-blue-500 outline-none transition-all"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </div>
                  <div className="flex gap-2 w-full md:w-auto overflow-x-auto no-scrollbar pb-1 md:pb-0">
                    <button className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-600 flex items-center gap-2 hover:bg-slate-50 transition-colors">
                      <Filter size={14} />
                      {t('extraction.workbench.filter')}
                    </button>
                    <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
                      {['all', 'L0', 'facts', 'constraints'].map(l => (
                        <button 
                          key={l}
                          onClick={() => setFilterLayer(l)}
                          className={cn(
                            "px-3 py-1 rounded-md text-[10px] font-bold uppercase transition-all",
                            filterLayer === l ? "bg-white text-slate-800 shadow-sm" : "text-slate-400 hover:text-slate-600"
                          )}
                        >
                          {t(`layers.${l}`)}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1 border-t border-slate-50">
                  <div className="flex items-center gap-3">
                     <button 
                       onClick={() => setIsSelectMode(!isSelectMode)}
                       className={cn(
                         "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all",
                         isSelectMode ? "bg-blue-50 text-blue-600" : "text-slate-500 hover:bg-slate-50"
                       )}
                     >
                       {isSelectMode ? <CheckSquare size={14} /> : <Square size={14} />}
                       {t('extraction.workbench.batchEdit')}
                     </button>
                     {isSelectMode && selectedIds.length > 0 && (
                       <motion.div 
                         initial={{ opacity: 0, scale: 0.9 }}
                         animate={{ opacity: 1, scale: 1 }}
                         className="flex items-center gap-2 px-3 py-1 bg-blue-600 text-white rounded-full text-[10px] font-bold"
                       >
                         已选 {selectedIds.length} 项
                       </motion.div>
                     )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button 
                      title={t('extraction.workbench.merge')}
                      className="p-2 text-slate-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-all"
                    >
                      <GitMerge size={16} />
                    </button>
                    <button 
                      title={t('extraction.workbench.archive')}
                      className="p-2 text-slate-400 hover:text-amber-500 hover:bg-amber-50 rounded-lg transition-all"
                    >
                      <Archive size={16} />
                    </button>
                    <button 
                      title={t('extraction.workbench.disable')}
                      className="p-2 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all"
                    >
                      <Ban size={16} />
                    </button>
                    <button 
                      title={t('extraction.workbench.rollback')}
                      className="p-2 text-slate-400 hover:text-indigo-500 hover:bg-indigo-50 rounded-lg transition-all"
                    >
                      <History size={16} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Memory List Table */}
              <div className="flex-1 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col min-h-0">
                <div className="overflow-x-auto h-full custom-scrollbar">
                  <table className="w-full text-left border-collapse min-w-[700px]">
                    <thead className="sticky top-0 bg-slate-50/80 backdrop-blur-sm z-10">
                      <tr className="border-b border-slate-100">
                        <th className="p-4 w-12"></th>
                        <th className="p-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">{t('extraction.workbench.edit')}</th>
                        <th className="p-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">记忆标题</th>
                        <th className="p-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">分层</th>
                        <th className="p-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">内容摘要</th>
                        <th className="p-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">最后更新</th>
                        <th className="p-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest text-right">状态</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {filteredMemories.map((m) => (
                        <tr 
                          key={m.id} 
                          className={cn(
                            "hover:bg-slate-50 group transition-colors",
                            selectedIds.includes(m.id) && "bg-blue-50/30"
                          )}
                        >
                          <td className="p-4">
                            <button 
                              onClick={() => toggleSelection(m.id)}
                              className={cn(
                                "transition-colors",
                                selectedIds.includes(m.id) ? "text-blue-500" : "text-slate-300"
                              )}
                            >
                              {selectedIds.includes(m.id) ? <CheckSquare size={16} /> : <Square size={16} />}
                            </button>
                          </td>
                          <td className="p-4">
                            <button className="p-1 px-3 border border-slate-200 text-slate-400 hover:text-blue-600 hover:border-blue-300 rounded text-[10px] font-bold transition-all">
                              EDIT
                            </button>
                          </td>
                          <td className="p-4">
                            <div className="font-bold text-xs text-slate-800">{m.title}</div>
                          </td>
                          <td className="p-4">
                             <span className={cn(
                               "px-2 py-0.5 rounded text-[9px] font-bold uppercase",
                               m.layer === 'L0' ? "bg-red-50 text-red-600" : "bg-slate-100 text-slate-500"
                             )}>
                               {t(`layers.${m.layer}`)}
                             </span>
                          </td>
                          <td className="p-4">
                            <div className="text-[11px] text-slate-500 truncate max-w-xs">{m.content}</div>
                          </td>
                          <td className="p-4">
                            <div className="text-[10px] text-slate-400 font-mono">2h ago</div>
                          </td>
                          <td className="p-4 text-right">
                             <div className="flex items-center justify-end gap-1.5">
                               <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                               <span className="text-[10px] font-bold text-emerald-600 uppercase">Active</span>
                             </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};
