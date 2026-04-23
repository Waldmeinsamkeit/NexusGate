import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Plus, 
  Search, 
  Filter, 
  Edit2, 
  Trash2, 
  Archive, 
  Lock, 
  ExternalLink, 
  Database, 
  Tag,
  X,
  AlertCircle,
  Download,
  CheckSquare,
  Square
} from 'lucide-react';
import { mockMemories } from '../services/mockData';
import { cn } from '../lib/utils';
import { motion, AnimatePresence } from 'motion/react';

const LayerBadge = ({ layer }: { layer: string }) => {
  const { t } = useTranslation();
  const colors: Record<string, string> = {
    L0: 'bg-red-50 text-red-700 border-red-100',
    constraints: 'bg-amber-50 text-amber-700 border-amber-100',
    procedures: 'bg-blue-50 text-blue-700 border-blue-100',
    continuity: 'bg-purple-50 text-purple-700 border-purple-100',
    facts: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  };

  return (
    <span className={cn("px-2 py-0.5 rounded text-[9px] font-bold uppercase border", colors[layer] || 'bg-slate-50 text-slate-700 border-slate-100')}>
      {t(`layers.${layer}`)}
    </span>
  );
};

export const MemoryCenter = () => {
  const { t } = useTranslation();
  
  /**
   * BACKEND INTEGRATION POINT:
   * Fetch all memory entries from the knowledge base.
   * Supports pagination, filtering by layer, and search queries.
   * Endpoint: GET /api/v1/memories?layer=facts&q=search_term&page=1
   */
  const memories = mockMemories; // Replace with state filled by actual API call

  const [activeLayer, setActiveLayer] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMemory, setEditingMemory] = useState<any>(null);
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const layers = ['all', 'L0', 'constraints', 'procedures', 'continuity', 'facts'];

  const openAddModal = () => {
    setEditingMemory(null);
    setIsModalOpen(true);
  };

  const openEditModal = (memory: any) => {
    setEditingMemory(memory);
    setIsModalOpen(true);
  };

  const handleDelete = (id: string) => {
    /**
     * BACKEND INTEGRATION POINT:
     * Delete a specific memory entry.
     * Endpoint: DELETE /api/v1/memories/:id
     */
    console.log('Deleting memory:', id);
    if (window.confirm(t('memory.delete') + '?')) {
      alert('条目已移除 (模拟)');
    }
  };

  const handleExport = () => {
    if (!isSelectMode) {
      setIsSelectMode(true);
      return;
    }

    if (selectedIds.length === 0) {
      alert('请至少选择一个记忆条库。');
      return;
    }

    const exportData = mockMemories.filter(m => selectedIds.includes(m.id));

    const markdown = exportData.map(m => (
      `# ${m.title}\n` +
      `**ID**: ${m.id}\n` +
      `**Layer**: ${m.layer}\n` +
      `**Confidence**: ${m.confidence}\n` +
      `**Tags**: ${m.tags.join(', ')}\n\n` +
      `${m.content}\n\n` +
      `---\n`
    )).join('\n');
    
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `NexusGate_Memories_${new Date().toISOString().split('T')[0]}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    setIsSelectMode(false);
    setSelectedIds([]);
    alert('选中的 Markdown 导出已生成并开始下载。');
  };

  const toggleSelection = (id: string) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const cancelSelection = () => {
    setIsSelectMode(false);
    setSelectedIds([]);
  };

  const filtered = mockMemories.filter(m => {
    const matchesLayer = activeLayer === 'all' || m.layer === activeLayer;
    const matchesSearch = m.title.toLowerCase().includes(search.toLowerCase()) || 
                         m.content.toLowerCase().includes(search.toLowerCase());
    return matchesLayer && matchesSearch;
  });

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <header className="flex justify-between items-center bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-800">{t('memory.title')}</h2>
          <p className="text-slate-400 text-[11px] font-medium uppercase tracking-tight">{t('memory.subtitle')}</p>
        </div>
        <div className="flex gap-2">
          <AnimatePresence>
            {isSelectMode && (
              <motion.button 
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                onClick={cancelSelection}
                className="px-4 py-2 text-xs font-bold text-rose-600 hover:bg-rose-50 rounded-lg transition-colors border border-rose-100"
              >
                {t('common.cancel')}
              </motion.button>
            )}
          </AnimatePresence>
          <button 
            onClick={handleExport}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-xs transition-all shadow-sm border",
              isSelectMode 
                ? "bg-emerald-600 border-emerald-500 text-white hover:bg-emerald-700" 
                : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
            )}
          >
            <Download size={14} />
            {isSelectMode ? `确认导出 (${selectedIds.length})` : t('memory.export')}
          </button>
          {!isSelectMode && (
            <button 
              onClick={openAddModal}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-bold text-xs flex items-center gap-2 transition-colors shadow-sm"
            >
              <Plus size={14} />
              {t('memory.add')}
            </button>
          )}
        </div>
      </header>

      <div className="flex gap-4 items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
          <input 
            type="text" 
            placeholder={t('memory.search')}
            className="w-full bg-white border border-slate-200 rounded-lg py-2 pl-9 pr-4 text-sm focus:ring-1 focus:ring-blue-500 outline-none shadow-sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {!isSelectMode && (
          <div className="flex gap-1 p-1 bg-white border border-slate-200 rounded-lg shadow-sm">
            {layers.map(layer => (
              <button
                key={layer}
                onClick={() => setActiveLayer(layer)}
                className={cn(
                  "px-3 py-1.5 text-[10px] font-bold rounded transition-colors",
                  activeLayer === layer ? "bg-slate-800 text-white" : "text-slate-500 hover:text-slate-800"
                )}
              >
                {t(`layers.${layer}`)}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((memory) => (
          <div 
            key={memory.id} 
            onClick={() => isSelectMode && toggleSelection(memory.id)}
            className={cn(
              "bg-white border rounded-lg shadow-sm group transition-all flex flex-col relative",
              isSelectMode ? "cursor-pointer" : "hover:border-blue-400",
              selectedIds.includes(memory.id) ? "border-emerald-500 ring-1 ring-emerald-500 ring-opacity-50" : "border-slate-200"
            )}
          >
            {isSelectMode && (
              <div className="absolute top-2 right-2 z-10">
                {selectedIds.includes(memory.id) ? (
                  <CheckSquare size={18} className="text-emerald-500 fill-emerald-50" />
                ) : (
                  <Square size={18} className="text-slate-300" />
                )}
              </div>
            )}
            <div className="p-4 flex-1">
              <div className="flex items-center gap-2 mb-3">
                <LayerBadge layer={memory.layer} />
                <div className="flex-1 min-w-0">
                  <h4 className="font-bold text-xs text-slate-800 truncate">{memory.title}</h4>
                </div>
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed mb-4 line-clamp-3 font-medium">
                {memory.content}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {memory.tags.map(tag => (
                  <span key={tag} className="text-[9px] font-bold text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100 uppercase">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
            {!isSelectMode && (
              <div className="px-4 py-2 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[10px] font-mono text-slate-400">{memory.id}</span>
                <div className="flex gap-1">
                  <button 
                    onClick={() => openEditModal(memory)}
                    className="p-1 hover:bg-white rounded text-slate-400 hover:text-blue-600 transition-colors"
                  >
                    <Edit2 size={12} />
                  </button>
                  <button 
                    onClick={() => handleDelete(memory.id)}
                    className="p-1 hover:bg-white rounded text-slate-400 hover:text-rose-600 transition-colors"
                  >
                    <Trash2 size={12} />
                  </button>
                  <button className="p-1 hover:bg-white rounded text-slate-400 hover:text-amber-600 transition-colors">
                    <Archive size={12} />
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      {/* Edit/Add Modal Interface */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <motion.div 
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden flex flex-col"
          >
            <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
              <h3 className="font-bold text-slate-800 flex items-center gap-2">
                <Database size={16} className="text-blue-600" />
                {editingMemory ? t('memory.edit') : t('memory.add')}
              </h3>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="p-1 hover:bg-slate-200 rounded-full text-slate-400 transition-colors"
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1.5 tracking-wider">标题 / 索引词</label>
                <input 
                  type="text" 
                  defaultValue={editingMemory?.title}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  placeholder="例如: System_Persona_Core"
                />
              </div>
              
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1.5 tracking-wider">分层 (Layer)</label>
                <select 
                  defaultValue={editingMemory?.layer || 'L0'}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                >
                  {layers.filter(l => l !== 'all').map(l => (
                    <option key={l} value={l}>{t(`layers.${l}`)}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1.5 tracking-wider">内容正文</label>
                <textarea 
                  rows={4}
                  defaultValue={editingMemory?.content}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                  placeholder="输入此条目的具体定义或属性内容..."
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1.5 tracking-wider">标签 (Tags)</label>
                <input 
                  type="text" 
                  defaultValue={editingMemory?.tags.join(', ')}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                  placeholder="用逗号分隔，例如: internal, logic"
                />
              </div>
            </div>
            
            <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3">
              <button 
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 text-xs font-bold text-slate-500 hover:text-slate-800 transition-colors"
              >
                {t('common.cancel')}
              </button>
              <button 
                onClick={() => {
                  /**
                   * BACKEND INTEGRATION POINT:
                   * Create or Update memory entry.
                   * Endpoint (Create): POST /api/v1/memories
                   * Endpoint (Update): PUT /api/v1/memories/:id
                   */
                  alert('数据已提交至 NexusGate 内核 (接口模拟)');
                  setIsModalOpen(false);
                }}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-bold text-xs shadow-sm transition-colors"
              >
                {t('common.save')}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </motion.div>
  );
};
