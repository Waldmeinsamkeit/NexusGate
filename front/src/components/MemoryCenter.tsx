import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  X,
  AlertCircle,
  RefreshCw,
  Check,
  Shield,
} from 'lucide-react';
import { fetchMemories, createMemory, updateMemory, archiveMemory, archiveMemoryLayer, type MemoryRecord } from '../services/api';
import { cn } from '../lib/utils';
import { motion, AnimatePresence } from 'motion/react';

/* ── layer config ─────────────────────────────────────────────────── */

const LAYER_COLORS: Record<string, string> = {
  L1: 'bg-amber-50 text-amber-700 border-amber-100',
  L2: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  L3: 'bg-blue-50 text-blue-700 border-blue-100',
  L4: 'bg-purple-50 text-purple-700 border-purple-100',
};

const LAYER_LABELS: Record<string, string> = {
  L1: '约束 L1',
  L2: '事实 L2',
  L3: '技能 L3',
  L4: '连续性 L4',
};

const LayerBadge = ({ layer }: { layer: string }) => (
  <span className={cn('px-2 py-0.5 rounded text-[9px] font-bold uppercase border', LAYER_COLORS[layer] || 'bg-slate-50 text-slate-700 border-slate-100')}>
    {LAYER_LABELS[layer] || layer}
  </span>
);

const LAYERS = ['all', 'L1', 'L2', 'L3', 'L4'] as const;

/* ── main component ───────────────────────────────────────────────── */

export const MemoryCenter = () => {
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeLayer, setActiveLayer] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMemory, setEditingMemory] = useState<MemoryRecord | null>(null);
  const [saving, setSaving] = useState(false);

  /* ── data loading ──────────────────────────────────────────────── */

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params: { layers?: string; query?: string } = {};
      if (activeLayer !== 'all') params.layers = activeLayer;
      if (search.trim()) params.query = search.trim();
      const res = await fetchMemories({ ...params, limit: 100 });
      setMemories(res.items || []);
    } catch (e: any) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [activeLayer, search]);

  useEffect(() => { load(); }, [load]);

  /* ── handlers ────────────────────────────────────────────────── */

  const openEdit = (mem: MemoryRecord) => { setEditingMemory(mem); setIsModalOpen(true); };
  const openAdd = () => { setEditingMemory(null); setIsModalOpen(true); };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确认归档此记忆条目？')) return;
    try {
      await archiveMemory(id);
      load();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleClearLayer = async () => {
    const layer = activeLayer === 'all' ? '' : activeLayer;
    if (!layer) { alert('请先选择一个具体层级'); return; }
    if (!window.confirm(`确认清空 ${layer} 层所有记忆？此操作不可恢复！`)) return;
    try {
      const res = await archiveMemoryLayer(layer);
      alert(`已归档 ${res.archived_count} 条 ${layer} 记忆`);
      load();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleSave = async (form: SaveForm) => {
    setSaving(true);
    const tags = form.tags.split(',').map(s => s.trim()).filter(Boolean);
    try {
      if (editingMemory) {
        await updateMemory(editingMemory.memory_id, {
          content: form.content,
          tags,
          verified: form.verified,
          layer: form.layer,
        });
      } else {
        await createMemory({
          content: form.content,
          layer: form.layer,
          tags,
          verified: form.verified,
          l1_index: form.l1Index,
        });
      }
      setIsModalOpen(false);
      setEditingMemory(null);
      load();
    } catch (e: any) {
      console.error('save failed:', e);
      alert('保存失败: ' + (e.message || e));
    } finally {
      setSaving(false);
    }
  };

  /* ── render ──────────────────────────────────────────────────── */

  if (error && memories.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle size={40} className="text-slate-300" />
        <p className="text-sm text-slate-500">{error}</p>
        <button onClick={load} className="text-xs text-blue-600 hover:underline">重试</button>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      {/* Header */}
      <header className="card-panel p-4 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-800">记忆工作台</h2>
          <p className="text-slate-400 text-[11px] font-medium uppercase tracking-tight">L1-L4 记忆管理</p>
        </div>
        <div className="flex gap-2 items-center">
          <button onClick={load} disabled={loading} className="p-1.5 hover:bg-slate-100 rounded-md text-slate-400 disabled:opacity-50">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
          {activeLayer !== 'all' && (
            <button onClick={handleClearLayer} className="bg-rose-50 hover:bg-rose-100 text-rose-600 px-3 py-2 rounded-lg font-bold text-xs flex items-center gap-1.5 transition-colors border border-rose-200">
              <Trash2 size={12} /> 清空此层
            </button>
          )}
          <button onClick={openAdd} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-bold text-xs flex items-center gap-2 transition-colors shadow-sm">
            <Plus size={14} /> 新建条目
          </button>
        </div>
      </header>

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
          <input
            type="text"
            placeholder="搜索记忆..."
            className="w-full bg-white border border-slate-200 rounded-lg py-2 pl-9 pr-4 text-sm focus:ring-1 focus:ring-blue-500 outline-none shadow-sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-1 p-1 bg-white border border-slate-200 rounded-lg shadow-sm">
          {LAYERS.map(layer => (
            <button
              key={layer}
              onClick={() => setActiveLayer(layer)}
              className={cn(
                'px-3 py-1.5 text-[10px] font-bold rounded transition-colors',
                activeLayer === layer ? 'bg-slate-800 text-white' : 'text-slate-500 hover:text-slate-800',
              )}
            >
              {layer === 'all' ? '全部' : LAYER_LABELS[layer] || layer}
            </button>
          ))}
        </div>
      </div>

      {/* Memory list */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {memories.map((mem) => (
          <div key={mem.memory_id} className="card-panel group hover:border-blue-400 transition-all flex flex-col">
            <div className="p-4 flex-1">
              <div className="flex items-center gap-2 mb-2">
                <LayerBadge layer={mem.layer} />
                {mem.verified && <Shield size={12} className="text-emerald-500" />}
                <span className="text-[9px] text-slate-400 font-mono ml-auto">{mem.scope}</span>
              </div>
              <p className="text-[11px] text-slate-700 leading-relaxed mb-3 line-clamp-4">{mem.content}</p>
              {mem.summary && (
                <p className="text-[10px] font-bold text-slate-500 mb-2 truncate">{mem.summary}</p>
              )}
              <div className="flex flex-wrap gap-1.5">
                {(mem.tags || []).map(tag => (
                  <span
                    key={tag}
                    className={cn(
                      'text-[9px] font-bold px-1.5 py-0.5 rounded border',
                      tag.startsWith('→L2:') ? 'text-emerald-600 bg-emerald-50 border-emerald-100' :
                      tag.startsWith('←L1:') ? 'text-amber-600 bg-amber-50 border-amber-100' :
                      tag.startsWith('L1:') ? 'text-amber-500 bg-amber-50/50 border-amber-100' :
                      tag.startsWith('L2:') ? 'text-emerald-500 bg-emerald-50/50 border-emerald-100' :
                      'text-slate-400 bg-slate-50 border-slate-100',
                    )}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
            <div className="px-4 py-2 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
              <span className="text-[9px] font-mono text-slate-400 truncate max-w-[140px]">{mem.memory_id}</span>
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={() => openEdit(mem)} className="p-1 hover:bg-white rounded text-slate-400 hover:text-blue-600"><Edit2 size={12} /></button>
                <button onClick={() => handleDelete(mem.memory_id)} className="p-1 hover:bg-white rounded text-slate-400 hover:text-rose-600"><Trash2 size={12} /></button>
              </div>
            </div>
          </div>
        ))}
        {memories.length === 0 && !loading && (
          <div className="col-span-full text-center py-12 text-slate-400 text-sm">暂无记忆条目</div>
        )}
      </div>

      {/* Edit modal */}
      <AnimatePresence>
        {isModalOpen && (
          <EditModal
            key={editingMemory?.memory_id || 'new'}
            memory={editingMemory}
            saving={saving}
            onSave={handleSave}
            onClose={() => { setIsModalOpen(false); setEditingMemory(null); }}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
};

/* ── edit modal ────────────────────────────────────────────────── */

interface SaveForm {
  layer: string;
  content: string;
  l1Index?: string;
  tags: string;
  verified: boolean;
}

const LAYER_OPTIONS_CREATE = [
  { id: 'L1L2', label: 'L1 + L2', desc: '索引 + 事实' },
  { id: 'L3',   label: 'L3',      desc: '技能' },
  { id: 'L4',   label: 'L4',      desc: '连续性' },
];

const LAYER_OPTIONS_EDIT = [
  { id: 'L1', label: 'L1', desc: '约束' },
  { id: 'L2', label: 'L2', desc: '事实' },
  { id: 'L3', label: 'L3', desc: '技能' },
  { id: 'L4', label: 'L4', desc: '连续性' },
];

const inputCls = 'w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none';

const EditModal: React.FC<{
  memory: MemoryRecord | null;
  saving: boolean;
  onSave: (form: SaveForm) => void;
  onClose: () => void;
}> = ({ memory, saving, onSave, onClose }) => {
  const isEdit = !!memory;
  const options = isEdit ? LAYER_OPTIONS_EDIT : LAYER_OPTIONS_CREATE;
  const defaultLayer = isEdit ? (memory.layer || 'L2') : 'L1L2';

  const [layer, setLayer] = useState(defaultLayer);
  const [l1Index, setL1Index] = useState('');
  const [content, setContent] = useState(memory?.content || '');
  const [tags, setTags] = useState((memory?.tags || []).join(', '));
  const [verified, setVerified] = useState(memory?.verified ?? true);

  const isL1L2 = layer === 'L1L2';
  const canSave = isL1L2 ? (l1Index.trim() && content.trim()) : content.trim();

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
          <h3 className="font-bold text-slate-800">{isEdit ? '编辑记忆' : '新建记忆'}</h3>
          <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded-full text-slate-400"><X size={18} /></button>
        </div>

        <div className="p-6 space-y-4">
          {isEdit && (
            <div className="flex items-center gap-2 text-[10px] text-slate-400">
              <span className="font-mono">{memory.memory_id}</span>
            </div>
          )}

          {/* Layer selector */}
          <div>
            <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1.5 tracking-wider">记忆层级</label>
            <div className="flex gap-2">
              {options.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setLayer(opt.id)}
                  className={cn(
                    'flex-1 py-2 rounded-lg text-xs font-bold border transition-all',
                    layer === opt.id
                      ? 'border-blue-500 bg-blue-50 text-blue-700 ring-1 ring-blue-500/30'
                      : 'border-slate-200 bg-white text-slate-500 hover:border-slate-300',
                  )}
                >
                  <div>{opt.label}</div>
                  <div className="text-[9px] font-normal mt-0.5">{opt.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* L1 index field — only in L1L2 create mode */}
          {isL1L2 && (
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1.5 tracking-wider">
                L1 索引 <span className="text-slate-300 font-normal">(指针，≤96 字符，如: 用户偏好 -&gt; 详细内容)</span>
              </label>
              <input
                type="text"
                value={l1Index}
                onChange={(e) => setL1Index(e.target.value)}
                maxLength={96}
                className={inputCls + ' font-mono'}
                placeholder="关键词 -> 描述方向, 例如: 代码风格偏好 -> 详细约束"
              />
              <div className="text-right text-[9px] text-slate-300 mt-0.5">{l1Index.length}/96</div>
            </div>
          )}

          {/* Content field */}
          <div>
            <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1.5 tracking-wider">
              {isL1L2 ? 'L2 事实内容' : '内容'}
            </label>
            <textarea
              rows={isL1L2 ? 4 : 5}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className={inputCls + ' resize-none'}
              placeholder={isL1L2 ? '对应的事实/约束详细内容...' : '记忆内容...'}
            />
          </div>

          {/* Tags */}
          <div>
            <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1.5 tracking-wider">标签</label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className={inputCls}
              placeholder="逗号分隔, 例如: arch, api"
            />
          </div>

          {/* Verified */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={verified} onChange={(e) => setVerified(e.target.checked)} className="rounded border-slate-300" />
            <span className="text-xs text-slate-600">已验证 (Verified)</span>
          </label>
        </div>

        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-xs font-bold text-slate-500 hover:text-slate-800">取消</button>
          <button
            onClick={() => onSave({ layer, content, l1Index: isL1L2 ? l1Index : undefined, tags, verified })}
            disabled={saving || !canSave}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-bold text-xs shadow-sm transition-colors flex items-center gap-2"
          >
            {saving ? <RefreshCw size={12} className="animate-spin" /> : <Check size={12} />}
            {isL1L2 ? '保存 L1 + L2' : '保存'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};
