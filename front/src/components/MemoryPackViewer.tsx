import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  RefreshCw,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Search,
  Layers,
  Scissors,
  CheckCircle,
  XCircle,
  Package,
  BarChart3,
  ArrowDown,
  Clock,
} from 'lucide-react';
import { fetchTraces, type TraceRecord } from '../services/api';
import { cn } from '../lib/utils';

/* ── helpers ─────────────────────────────────────────────────── */

const Num = ({ v, unit }: { v?: number; unit?: string }) => (
  <span className="font-mono font-bold text-slate-800">
    {v != null ? v.toLocaleString() : '-'}{unit && <span className="text-slate-400 text-[9px] ml-0.5">{unit}</span>}
  </span>
);

const SectionTag = ({ name, cls }: { name: string; cls?: string }) => (
  <span className={cn('px-1.5 py-0.5 rounded text-[9px] font-bold uppercase border', cls || 'bg-slate-50 text-slate-600 border-slate-100')}>{name}</span>
);

const SECTION_COLORS: Record<string, string> = {
  constraints: 'bg-amber-50 text-amber-700 border-amber-100',
  facts: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  procedures: 'bg-blue-50 text-blue-700 border-blue-100',
  continuity: 'bg-purple-50 text-purple-700 border-purple-100',
};

const SECTION_LABELS: Record<string, string> = {
  constraints: 'L1 约束',
  facts: 'L2 事实',
  procedures: 'L3 技能',
  continuity: 'L4 连续性',
};

/* ── collapsible panel ───────────────────────────────────────── */

const Panel = ({ title, icon: Icon, defaultOpen = false, badge, children }: {
  title: string;
  icon: React.ElementType;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
  children: React.ReactNode;
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card-panel overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full p-4 flex items-center gap-3 text-left hover:bg-slate-50 transition-colors"
      >
        <Icon size={16} className="text-blue-500 shrink-0" />
        <span className="text-sm font-bold text-slate-800 flex-1">{title}</span>
        {badge}
        {open ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 border-t border-slate-100 pt-3">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

/* ── detail view for a single trace ──────────────────────────── */

const TraceDetail = ({ trace }: { trace: TraceRecord }) => {
  const t = trace.trace;
  const retrieval = t.retrieval;
  const assembly = t.assembly;
  const render = t.render;
  const routing = t.routing;
  const budget = t.budget;
  const ts = trace.token_stats;

  const totalAssembly = (assembly?.facts_count || 0) + (assembly?.procedures_count || 0) + (assembly?.continuity_count || 0) + (assembly?.constraints_count || 0);
  const droppedCount = render?.dropped_blocks?.length || 0;
  const keptCount = render?.rendered_block_order?.length || 0;
  const hasRenderData = render && (render.estimated_tokens_before || render.trim_passes || render.trimmed_total_chars);
  const hasBudgetData = budget && (budget.before_tokens || budget.after_tokens || budget.enabled);

  const rawInput = ts.raw_input_tokens || 0;
  const sentTokens = ts.estimated_sent_tokens || ts.prompt_tokens || 0;
  const savedEst = ts.saved_tokens_estimated || 0;
  const savedRate = ts.saved_rate_estimated || 0;

  return (
    <div className="space-y-3">
      {/* 0. Token Stats Overview */}
      <Panel title="Token 统计" icon={BarChart3} defaultOpen badge={
        rawInput > 0 ? <span className="text-[9px] font-mono text-slate-400">节省 {Math.round(savedRate * 100)}%</span> : null
      }>
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-3">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-[9px] text-slate-400 font-bold uppercase">原始输入</span>
              <p className="mt-1"><Num v={rawInput} unit="tok" /></p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
              <span className="text-[9px] text-blue-600 font-bold uppercase">实际发送</span>
              <p className="mt-1"><Num v={sentTokens} unit="tok" /></p>
            </div>
            <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-100">
              <span className="text-[9px] text-emerald-600 font-bold uppercase">节省</span>
              <p className="mt-1"><Num v={savedEst} unit="tok" /></p>
            </div>
            <div className="p-3 bg-amber-50 rounded-lg border border-amber-100">
              <span className="text-[9px] text-amber-600 font-bold uppercase">节省率</span>
              <p className="mt-1 text-xs font-mono font-bold text-amber-700">{rawInput > 0 ? `${Math.round(savedRate * 100)}%` : '-'}</p>
            </div>
          </div>
          {rawInput > 0 && (
            <div className="space-y-2">
              <p className="text-[10px] font-bold text-slate-500">发送量对比</p>
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex justify-between text-[9px] text-slate-400 mb-1">
                    <span>原始输入</span>
                    <span className="font-mono">{rawInput} tok</span>
                  </div>
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: '100%' }} />
                  </div>
                </div>
                <ArrowDown size={14} className="text-slate-300 shrink-0" />
                <div className="flex-1">
                  <div className="flex justify-between text-[9px] text-slate-400 mb-1">
                    <span>实际发送</span>
                    <span className="font-mono">{sentTokens} tok</span>
                  </div>
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: `${Math.max(5, (sentTokens / Math.max(rawInput, 1)) * 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-2 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-[9px] text-slate-400 font-bold uppercase">完成 tokens</span>
              <p className="mt-1"><Num v={ts.completion_tokens} unit="tok" /></p>
            </div>
            <div className="p-2 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-[9px] text-slate-400 font-bold uppercase">数据来源</span>
              <p className="mt-1 text-[10px] font-mono text-slate-600">{ts.usage_source || '-'}</p>
            </div>
            <div className="p-2 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-[9px] text-slate-400 font-bold uppercase">API</span>
              <p className="mt-1 text-[10px] font-mono text-slate-600">{trace.api_style}</p>
            </div>
          </div>
        </div>
      </Panel>

      {/* 1. Retrieval */}
      <Panel title="检索阶段 — 命中的记忆候选" icon={Search} defaultOpen badge={
        retrieval ? <span className="text-[9px] font-mono text-slate-400">{retrieval.kept_candidates || 0}/{retrieval.raw_candidates || 0} 命中</span> : null
      }>
        {retrieval ? (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-400 font-bold uppercase">原始候选</span>
                <p className="mt-1"><Num v={retrieval.raw_candidates} /></p>
              </div>
              <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                <span className="text-[9px] text-emerald-600 font-bold uppercase">保留</span>
                <p className="mt-1"><Num v={retrieval.kept_candidates} /></p>
              </div>
              <div className="p-3 bg-red-50 rounded-lg border border-red-100">
                <span className="text-[9px] text-red-600 font-bold uppercase">淘汰</span>
                <p className="mt-1"><Num v={retrieval.dropped_candidates} /></p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-400 font-bold uppercase">记忆预算</span>
                <p className="mt-1"><Num v={retrieval.memory_budget_tokens} unit="tok" /></p>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-400 font-bold uppercase">字符预算</span>
                <p className="mt-1"><Num v={retrieval.memory_budget_chars} unit="chars" /></p>
              </div>
            </div>
            {retrieval.dropped_reasons && retrieval.dropped_reasons.length > 0 && (
              <div>
                <p className="text-[10px] font-bold text-slate-500 mb-1.5">淘汰原因</p>
                <div className="flex flex-wrap gap-1">
                  {retrieval.dropped_reasons.map((r, i) => (
                    <span key={i} className="text-[9px] px-2 py-0.5 bg-red-50 text-red-600 rounded border border-red-100 font-mono">{r}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : <p className="text-xs text-slate-400">无检索数据（记忆可能未启用）</p>}
      </Panel>

      {/* 2. Assembly */}
      <Panel title="组装阶段 — 结构化 MemoryPack" icon={Package} badge={
        <span className="text-[9px] font-mono text-slate-400">{totalAssembly} 条目</span>
      }>
        {assembly ? (
          <div className="grid grid-cols-4 gap-3">
            {(['constraints', 'facts', 'procedures', 'continuity'] as const).map(section => {
              const key = `${section}_count` as keyof typeof assembly;
              return (
                <div key={section} className="text-center p-3 rounded-lg border border-slate-100 bg-slate-50">
                  <SectionTag name={SECTION_LABELS[section] || section} cls={SECTION_COLORS[section]} />
                  <p className="mt-2"><Num v={assembly[key] as number | undefined} /></p>
                </div>
              );
            })}
          </div>
        ) : <p className="text-xs text-slate-400">无组装数据</p>}
      </Panel>

      {/* 3. Memory Render + Trim */}
      <Panel title="记忆渲染 & 裁剪" icon={Scissors} badge={
        hasRenderData ? (
          <span className="text-[9px] font-mono text-slate-400">
            {render!.estimated_tokens_before || 0} → {render!.estimated_tokens_after || 0} tok
          </span>
        ) : null
      }>
        {hasRenderData ? (
          <div className="space-y-4">
            {/* Token diff bar */}
            <div className="space-y-2">
              <p className="text-[10px] font-bold text-slate-500">Token 变化</p>
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex justify-between text-[9px] text-slate-400 mb-1">
                    <span>裁剪前</span>
                    <span className="font-mono">{render!.estimated_tokens_before || 0} tok</span>
                  </div>
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: '100%' }} />
                  </div>
                </div>
                <ArrowDown size={14} className="text-slate-300 shrink-0" />
                <div className="flex-1">
                  <div className="flex justify-between text-[9px] text-slate-400 mb-1">
                    <span>裁剪后</span>
                    <span className="font-mono">{render!.estimated_tokens_after || 0} tok</span>
                  </div>
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: `${Math.max(5, ((render!.estimated_tokens_after || 0) / Math.max(render!.estimated_tokens_before || 1, 1)) * 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Trim stats */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-400 font-bold uppercase">裁剪次数</span>
                <p className="mt-1"><Num v={render!.trim_passes} /></p>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-400 font-bold uppercase">裁剪字符</span>
                <p className="mt-1"><Num v={render!.trimmed_total_chars} unit="ch" /></p>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-400 font-bold uppercase">最终字符</span>
                <p className="mt-1"><Num v={render!.final_total_chars} unit="ch" /></p>
              </div>
            </div>

            {/* Per-layer trim */}
            <div>
              <p className="text-[10px] font-bold text-slate-500 mb-2">各层裁剪量</p>
              <div className="grid grid-cols-4 gap-2">
                {[
                  { label: 'L1 约束', val: render!.trimmed_l1_chars, color: 'amber' },
                  { label: 'L2 事实', val: render!.trimmed_l2_chars, color: 'emerald' },
                  { label: 'L3 技能', val: render!.trimmed_l3_chars, color: 'blue' },
                  { label: 'L4 连续性', val: render!.trimmed_l4_chars, color: 'purple' },
                ].map(({ label, val, color }) => (
                  <div key={label} className={cn('p-2 rounded-lg border text-center', val ? `bg-${color}-50 border-${color}-100` : 'bg-slate-50 border-slate-100')}>
                    <p className="text-[9px] font-bold text-slate-500">{label}</p>
                    <p className={cn('text-xs font-mono font-bold mt-0.5', val ? `text-${color}-700` : 'text-slate-300')}>
                      {val ? `-${val}` : '0'}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Retained counts by section */}
            {render!.retained_counts_by_section && (
              <div>
                <p className="text-[10px] font-bold text-slate-500 mb-2">保留条目数</p>
                <div className="grid grid-cols-4 gap-2">
                  {Object.entries(render!.retained_counts_by_section).map(([section, count]) => (
                    <div key={section} className="p-2 rounded-lg border border-slate-100 bg-emerald-50 text-center">
                      <p className="text-[9px] font-bold text-slate-500">{SECTION_LABELS[section] || section}</p>
                      <p className="text-xs font-mono font-bold text-emerald-700 mt-0.5">{count}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Kept block IDs */}
            {render!.rendered_block_order && render!.rendered_block_order.length > 0 && (
              <div>
                <p className="text-[10px] font-bold text-emerald-600 mb-1.5 flex items-center gap-1">
                  <CheckCircle size={10} /> 保留的 blocks ({keptCount})
                </p>
                <div className="flex flex-wrap gap-1">
                  {render!.rendered_block_order.map((id, i) => {
                    const section = id.split(':')[0];
                    return (
                      <span key={i} className={cn('text-[8px] px-1.5 py-0.5 rounded border font-mono', SECTION_COLORS[section] || 'bg-slate-50 text-slate-600 border-slate-100')}>
                        {id}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Dropped block IDs */}
            {render!.dropped_block_ids && render!.dropped_block_ids.length > 0 && (
              <div>
                <p className="text-[10px] font-bold text-red-600 mb-1.5 flex items-center gap-1">
                  <XCircle size={10} /> 被裁剪的 blocks ({droppedCount})
                </p>
                <div className="flex flex-wrap gap-1">
                  {render!.dropped_block_ids.map((id, i) => (
                    <span key={i} className="text-[8px] px-1.5 py-0.5 rounded border border-red-100 bg-red-50 text-red-600 font-mono line-through">{id}</span>
                  ))}
                </div>
                {render!.drop_reason_by_block && (
                  <div className="mt-2 space-y-1">
                    {Object.entries(render!.drop_reason_by_block).map(([blockId, reason]) => (
                      <div key={blockId} className="text-[9px] flex gap-2">
                        <span className="font-mono text-red-500 truncate max-w-[200px]">{blockId}</span>
                        <span className="text-slate-400">→</span>
                        <span className="text-slate-600">{reason}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Sections after trim */}
            {render!.sections_after && (
              <div>
                <p className="text-[10px] font-bold text-slate-500 mb-2">裁剪后各 section 内容</p>
                <div className="space-y-2">
                  {Object.entries(render!.sections_after).map(([section, content]) => (
                    <div key={section} className="rounded-lg border border-slate-100 overflow-hidden">
                      <div className={cn('px-3 py-1.5 border-b', SECTION_COLORS[section]?.replace('text-', 'bg-').split(' ')[0] || 'bg-slate-50')}>
                        <SectionTag name={SECTION_LABELS[section] || section} cls={SECTION_COLORS[section]} />
                      </div>
                      <pre className="px-3 py-2 text-[10px] text-slate-700 whitespace-pre-wrap break-all bg-white font-mono leading-relaxed max-h-40 overflow-y-auto custom-scrollbar">
                        {content || '(empty)'}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : <p className="text-xs text-slate-400">无记忆裁剪数据</p>}
      </Panel>

      {/* 3b. Context Budget */}
      <Panel title="上下文预算 & 裁剪" icon={BarChart3} badge={
        hasBudgetData ? (
          <span className="text-[9px] font-mono text-slate-400">
            {budget!.before_tokens || 0} → {budget!.after_tokens || 0} tok
            {budget!.native_tools_budget ? ' · tools' : ''}
          </span>
        ) : null
      }>
        {hasBudgetData ? (
          <div className="space-y-4">
            {/* Budget status */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-400 font-bold uppercase">状态</span>
                <p className="mt-1 text-xs font-mono font-bold">
                  {budget!.skipped ? <span className="text-amber-600">跳过</span> : budget!.enabled ? <span className="text-emerald-600">启用</span> : <span className="text-slate-400">未启用</span>}
                </p>
                {budget!.skip_reason && <p className="text-[9px] text-amber-500 mt-0.5">{budget!.skip_reason}</p>}
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-400 font-bold uppercase">上下文预算</span>
                <p className="mt-1"><Num v={budget!.context_budget_tokens} unit="tok" /></p>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-400 font-bold uppercase">Prompt 预算</span>
                <p className="mt-1"><Num v={budget!.prompt_budget_tokens} unit="tok" /></p>
              </div>
            </div>

            {/* Token diff bar */}
            <div className="space-y-2">
              <p className="text-[10px] font-bold text-slate-500">Token 变化</p>
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex justify-between text-[9px] text-slate-400 mb-1">
                    <span>预算前</span>
                    <span className="font-mono">{budget!.before_tokens || 0} tok</span>
                  </div>
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: '100%' }} />
                  </div>
                </div>
                <ArrowDown size={14} className="text-slate-300 shrink-0" />
                <div className="flex-1">
                  <div className="flex justify-between text-[9px] text-slate-400 mb-1">
                    <span>预算后</span>
                    <span className="font-mono">{budget!.after_tokens || 0} tok</span>
                  </div>
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: `${Math.max(5, ((budget!.after_tokens || 0) / Math.max(budget!.before_tokens || 1, 1)) * 100)}%` }}
                    />
                  </div>
                </div>
              </div>
              {(budget!.over_budget_before || budget!.over_budget_after) && (
                <div className="flex gap-2">
                  {budget!.over_budget_before && <span className="text-[9px] px-2 py-0.5 bg-amber-50 text-amber-600 rounded border border-amber-100 font-mono">预算前超限</span>}
                  {budget!.over_budget_after && <span className="text-[9px] px-2 py-0.5 bg-red-50 text-red-600 rounded border border-red-100 font-mono">预算后仍超限</span>}
                </div>
              )}
            </div>

            {/* Trim stats */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-400 font-bold uppercase">截断消息</span>
                <p className="mt-1"><Num v={budget!.truncated_messages} /></p>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-400 font-bold uppercase">丢弃消息</span>
                <p className="mt-1"><Num v={budget!.dropped_messages} /></p>
              </div>
            </div>

            {/* Tool episode budget (native) */}
            {budget!.native_tools_budget && (
              <div>
                <p className="text-[10px] font-bold text-slate-500 mb-2">工具 Episode 裁剪</p>
                <div className="grid grid-cols-4 gap-2">
                  <div className="p-2 rounded-lg border border-slate-100 bg-slate-50 text-center">
                    <p className="text-[9px] font-bold text-slate-500">Episodes</p>
                    <p className="text-xs font-mono font-bold text-slate-800 mt-0.5">{budget!.episode_count || 0}</p>
                  </div>
                  <div className="p-2 rounded-lg border border-amber-100 bg-amber-50 text-center">
                    <p className="text-[9px] font-bold text-amber-600">截断</p>
                    <p className="text-xs font-mono font-bold text-amber-700 mt-0.5">{budget!.episodes_trimmed || 0}</p>
                  </div>
                  <div className="p-2 rounded-lg border border-blue-100 bg-blue-50 text-center">
                    <p className="text-[9px] font-bold text-blue-600">摘要化</p>
                    <p className="text-xs font-mono font-bold text-blue-700 mt-0.5">{budget!.episodes_summarized || 0}</p>
                  </div>
                  <div className="p-2 rounded-lg border border-purple-100 bg-purple-50 text-center">
                    <p className="text-[9px] font-bold text-purple-600">结果裁剪</p>
                    <p className="text-xs font-mono font-bold text-purple-700 mt-0.5">{budget!.tool_result_pruned_chars || 0}<span className="text-[9px] text-purple-400 ml-0.5">ch</span></p>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : <p className="text-xs text-slate-400">无上下文预算数据</p>}
      </Panel>

      {/* 4. Routing */}
      <Panel title="路由决策" icon={Layers} badge={
        routing ? <span className="text-[9px] font-mono text-slate-400">{routing.provider}/{routing.model}</span> : null
      }>
        {routing ? (
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-[9px] text-slate-400 font-bold uppercase">Provider</span>
              <p className="font-mono font-bold text-slate-800 mt-1 text-sm">{routing.provider || '-'}</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-[9px] text-slate-400 font-bold uppercase">Model</span>
              <p className="font-mono font-bold text-slate-800 mt-1 text-sm truncate">{routing.model || '-'}</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-[9px] text-slate-400 font-bold uppercase">Context Budget</span>
              <p className="mt-1"><Num v={routing.context_budget} unit="tok" /></p>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-[9px] text-slate-400 font-bold uppercase">Grounding</span>
              <p className="font-mono text-slate-800 mt-1 text-xs">{routing.grounding_mode || '-'} / {routing.grounding_policy || '-'}</p>
            </div>
            {routing.reason_codes && routing.reason_codes.length > 0 && (
              <div className="col-span-2 p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-400 font-bold uppercase">Reason Codes</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {routing.reason_codes.map((c, i) => (
                    <span key={i} className="text-[9px] px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded border border-blue-100 font-mono">{c}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : <p className="text-xs text-slate-400">无路由数据</p>}
      </Panel>
    </div>
  );
};

/* ── main component ──────────────────────────────────────────── */

export const MemoryPackViewer = () => {
  const [traces, setTraces] = useState<TraceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<TraceRecord | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetchTraces(200);
      setTraces(res.items);
      if (res.items.length > 0 && !selected) {
        setSelected(res.items[0]);
      }
    } catch (e: any) {
      setError(e.message || '无法加载');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const hasMemoryData = (t: TraceRecord) => !!(t.trace.retrieval || t.trace.assembly || t.trace.render || t.trace.budget);

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      {/* Header */}
      <header className="card-panel p-4 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-800">Memory Pack 透视</h2>
          <p className="text-slate-400 text-[11px] font-medium uppercase tracking-tight">查看每次请求的记忆组装、渲染与裁剪过程</p>
        </div>
        <button onClick={load} disabled={loading} className="p-1.5 hover:bg-slate-100 rounded-md text-slate-400 disabled:opacity-50">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </header>

      {error && !traces.length && (
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <AlertCircle size={40} className="text-slate-300" />
          <p className="text-sm text-slate-500">{error}</p>
        </div>
      )}

      <div className="flex gap-4 items-start">
        {/* Trace list */}
        <div className="w-80 shrink-0 space-y-1 max-h-[calc(100vh-200px)] overflow-y-auto custom-scrollbar">
          {traces.length === 0 && !loading && (
            <p className="text-xs text-slate-400 text-center py-8">暂无请求记录。发送一次 API 请求后刷新查看。</p>
          )}
          {traces.map((t) => {
            const isSelected = selected?.request_id === t.request_id;
            const hasMem = hasMemoryData(t);
            return (
              <button
                key={t.request_id}
                onClick={() => setSelected(t)}
                className={cn(
                  'w-full text-left p-3 rounded-lg border transition-all',
                  isSelected ? 'bg-blue-50 border-blue-200 ring-1 ring-blue-500/30' : 'bg-white border-slate-100 hover:border-slate-200',
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={cn('w-1.5 h-1.5 rounded-full', hasMem ? 'bg-emerald-500' : 'bg-slate-300')} />
                  <span className="text-[10px] font-mono font-bold text-slate-800 truncate">{t.request_id}</span>
                </div>
                <div className="flex items-center gap-2 text-[9px] text-slate-400">
                  <Clock size={9} />
                  <span>{new Date(t.created_at * 1000).toLocaleTimeString()}</span>
                  <span className="mx-0.5">·</span>
                  <span className="font-mono">{t.model || '-'}</span>
                  <span className="mx-0.5">·</span>
                  <span>{t.latency_ms}ms</span>
                </div>
                {hasMem && (
                  <div className="flex gap-1 mt-1.5">
                    {t.trace.assembly && <span className="text-[8px] px-1 py-0.5 bg-emerald-50 text-emerald-600 rounded border border-emerald-100">
                      {(t.trace.assembly.facts_count || 0) + (t.trace.assembly.procedures_count || 0) + (t.trace.assembly.continuity_count || 0) + (t.trace.assembly.constraints_count || 0)} items
                    </span>}
                    {t.trace.render?.trim_passes ? <span className="text-[8px] px-1 py-0.5 bg-amber-50 text-amber-600 rounded border border-amber-100">
                      {t.trace.render.trim_passes} trims
                    </span> : null}
                    {t.trace.budget && !t.trace.assembly && <span className="text-[8px] px-1 py-0.5 bg-blue-50 text-blue-600 rounded border border-blue-100">
                      budget
                    </span>}
                  </div>
                )}
              </button>
            );
          })}
        </div>

        {/* Detail panel */}
        <div className="flex-1 min-w-0">
          {selected ? (
            <TraceDetail trace={selected} />
          ) : (
            <div className="flex flex-col items-center justify-center h-64 gap-4">
              <Package size={40} className="text-slate-200" />
              <p className="text-sm text-slate-400">选择一个请求查看 Memory Pack 详情</p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};
