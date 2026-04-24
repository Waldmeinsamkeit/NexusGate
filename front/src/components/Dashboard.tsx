import { useState, useEffect, useCallback } from 'react';
import { cn, formatNumber } from '../lib/utils';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { RefreshCw, ChevronRight, AlertCircle, BarChart3 } from 'lucide-react';
import { fetchHealth, fetchTraces, type HealthResponse, type TraceRecord } from '../services/api';
import { motion, AnimatePresence } from 'motion/react';

/* ── helpers ──────────────────────────────────────────────────────── */

interface AggregatedStats {
  totalRequests: number;
  totalRawTokens: number;
  totalSentTokens: number;
  totalSaved: number;
  savedRate: number;
}

function aggregateTraces(traces: TraceRecord[]): AggregatedStats {
  let totalRaw = 0;
  let totalSent = 0;
  let totalSaved = 0;
  for (const t of traces) {
    const ts = t.token_stats;
    if (!ts) continue;
    totalRaw += ts.raw_input_tokens || ts.estimated_prompt_tokens || 0;
    totalSent += ts.prompt_tokens || ts.estimated_sent_tokens || 0;
    totalSaved += Math.max(ts.saved_tokens_actual || ts.saved_tokens_estimated || 0, 0);
  }
  const clampedSaved = Math.max(totalSaved, 0);
  const effectiveRaw = Math.max(totalRaw, clampedSaved);
  return {
    totalRequests: traces.length,
    totalRawTokens: totalRaw,
    totalSentTokens: totalSent,
    totalSaved: clampedSaved,
    savedRate: effectiveRaw > 0 ? Math.min(clampedSaved / effectiveRaw, 1.0) : 0,
  };
}

interface DayBucket {
  date: string;
  raw: number;
  sent: number;
  saved: number;
}

function bucketByDay(traces: TraceRecord[]): DayBucket[] {
  const map = new Map<string, DayBucket>();
  for (const t of traces) {
    const ts = t.token_stats;
    if (!ts) continue;
    const day = t.created_at ? new Date(t.created_at * 1000).toISOString().slice(0, 10) : 'unknown';
    let bucket = map.get(day);
    if (!bucket) {
      bucket = { date: day, raw: 0, sent: 0, saved: 0 };
      map.set(day, bucket);
    }
    bucket.raw += ts.raw_input_tokens || ts.estimated_prompt_tokens || 0;
    bucket.sent += ts.prompt_tokens || ts.estimated_sent_tokens || 0;
    bucket.saved += ts.saved_tokens_actual || ts.saved_tokens_estimated || 0;
  }
  return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date)).slice(-7);
}

/* ── stat card ────────────────────────────────────────────────────── */

const StatCard = ({ title, value, sub, color }: { title: string; value: string; sub?: string; color?: string }) => (
  <div className="card-panel p-4">
    <h3 className="text-[10px] text-slate-400 font-bold uppercase mb-1 tracking-wider">{title}</h3>
    <div className="flex items-end justify-between">
      <span className={cn('text-2xl font-mono font-bold tracking-tight', color || 'text-slate-800')}>{value}</span>
      {sub && <span className="text-slate-400 text-[10px] mb-1 font-medium">{sub}</span>}
    </div>
  </div>
);

/* ── trace detail modal ───────────────────────────────────────────── */

const TraceDetail = ({ trace, onClose }: { trace: TraceRecord; onClose: () => void }) => {
  const ts = trace.token_stats;
  const hist = trace.trace?.history;
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
        className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-5 border-b border-slate-100 flex justify-between items-center">
          <h3 className="text-sm font-bold text-slate-800">请求详情</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-lg">&times;</button>
        </div>
        <div className="p-5 space-y-4 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <span className="text-slate-400 font-bold text-[10px] uppercase">模型</span>
              <p className="font-mono text-slate-800 mt-0.5">{trace.model || '-'}</p>
            </div>
            <div>
              <span className="text-slate-400 font-bold text-[10px] uppercase">时间</span>
              <p className="font-mono text-slate-800 mt-0.5">{trace.created_at ? new Date(trace.created_at * 1000).toLocaleString('zh-CN') : '-'}</p>
            </div>
          </div>

          <div className="bg-slate-50 rounded-lg p-3 border border-slate-100 space-y-2">
            <h4 className="text-[10px] font-bold text-slate-500 uppercase">Token 明细</h4>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="flex justify-between"><span className="text-slate-500">原始输入</span><span className="font-mono font-bold">{formatNumber(ts?.raw_input_tokens || ts?.estimated_prompt_tokens || 0)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">实际发送</span><span className="font-mono font-bold text-blue-600">{formatNumber(ts?.prompt_tokens || ts?.estimated_sent_tokens || 0)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">完成 tokens</span><span className="font-mono font-bold">{formatNumber(ts?.completion_tokens || 0)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">节省</span><span className="font-mono font-bold text-emerald-600">{formatNumber(ts?.saved_tokens_actual || ts?.saved_tokens_estimated || 0)}</span></div>
            </div>
            {ts && (ts.saved_rate_actual > 0 || ts.saved_rate_estimated > 0) && (
              <div className="text-[10px] text-emerald-600 font-bold">
                节省率: {((ts.saved_rate_actual || ts.saved_rate_estimated) * 100).toFixed(1)}%
              </div>
            )}
          </div>

          {hist && (
            <div className="bg-slate-50 rounded-lg p-3 border border-slate-100 space-y-2">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase">历史压缩</h4>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="flex justify-between"><span className="text-slate-500">模式</span><span className="font-mono">{hist.mode || '-'}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">压缩节省</span><span className="font-mono font-bold">{formatNumber(hist.history_replaced_tokens || 0)}</span></div>
              </div>
            </div>
          )}

          {trace.trace?.route_decision && (
            <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase mb-1">路由决策</h4>
              <p className="text-[11px] text-slate-700">{trace.trace.route_decision}</p>
            </div>
          )}

          {trace.error && (
            <div className="bg-red-50 rounded-lg p-3 border border-red-100">
              <h4 className="text-[10px] font-bold text-red-500 uppercase mb-1">错误</h4>
              <p className="text-[11px] text-red-700 break-all">{trace.error}</p>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
};

/* ── main dashboard ───────────────────────────────────────────────── */

export const Dashboard = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [traces, setTraces] = useState<TraceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedTrace, setSelectedTrace] = useState<TraceRecord | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, t] = await Promise.all([fetchHealth(), fetchTraces(200)]);
      setHealth(h);
      setTraces(t.items || []);
    } catch (e: any) {
      setError(e.message || '无法连接后端');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const stats = aggregateTraces(traces);
  const chartData = bucketByDay(traces);

  if (error && !health) {
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
      {/* Status bar */}
      <div className="card-panel p-3 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs">
          <span className={cn(
            'flex items-center gap-1.5 px-2 py-0.5 rounded-full font-bold text-[10px]',
            health?.status === 'ok' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : 'bg-amber-50 text-amber-700 border border-amber-100',
          )}>
            <span className={cn('w-1.5 h-1.5 rounded-full', health?.status === 'ok' ? 'bg-emerald-500' : 'bg-amber-500')} />
            {health?.status === 'ok' ? '运行中' : '未连接'}
          </span>
          <span className="text-slate-400 text-[10px]">上游: <span className="text-slate-700 font-mono">{health?.upstream || '-'}</span></span>
          <span className="text-slate-400 text-[10px]">模式: <span className="text-slate-700 font-mono">{health?.upstream_mode || '-'}</span></span>
        </div>
        <button onClick={load} disabled={loading} className="p-1.5 hover:bg-slate-100 rounded-md text-slate-400 transition-colors disabled:opacity-50">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="总请求数" value={formatNumber(stats.totalRequests)} sub="近期请求" />
        <StatCard title="原始 Token" value={formatNumber(stats.totalRawTokens)} sub="不使用架构时" />
        <StatCard title="实际发送" value={formatNumber(stats.totalSentTokens)} color="text-blue-600" sub="优化后发送" />
        <StatCard
          title="累计节省"
          value={formatNumber(stats.totalSaved)}
          color="text-emerald-600"
          sub={stats.savedRate > 0 ? `${(stats.savedRate * 100).toFixed(1)}% 节省率` : '-'}
        />
      </div>

      {/* Token trend chart */}
      {chartData.length > 1 && (
        <div className="card-panel p-5">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h4 className="text-sm font-bold text-slate-800">Token 趋势</h4>
              <p className="text-[10px] text-slate-400">按日汇总的 Token 使用与节省</p>
            </div>
            <div className="flex gap-4">
              <span className="flex items-center gap-1.5 text-[10px] text-slate-500 font-bold"><span className="w-2 h-2 bg-slate-300 rounded-sm" /> 原始</span>
              <span className="flex items-center gap-1.5 text-[10px] text-slate-500 font-bold"><span className="w-2 h-2 bg-blue-500 rounded-sm" /> 实际发送</span>
              <span className="flex items-center gap-1.5 text-[10px] text-emerald-600 font-bold"><span className="w-2 h-2 bg-emerald-500 rounded-sm" /> 节省</span>
            </div>
          </div>
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="gRaw" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#f1f5f9" stopOpacity={0.8}/><stop offset="95%" stopColor="#f1f5f9" stopOpacity={0}/></linearGradient>
                  <linearGradient id="gSent" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/><stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/></linearGradient>
                  <linearGradient id="gSaved" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.15}/><stop offset="95%" stopColor="#10b981" stopOpacity={0}/></linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} hide />
                <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '11px' }} />
                <Area type="monotone" dataKey="raw" stroke="#cbd5e1" fill="url(#gRaw)" name="原始 Token" />
                <Area type="monotone" dataKey="sent" stroke="#3b82f6" strokeWidth={2} fill="url(#gSent)" name="实际发送" />
                <Area type="monotone" dataKey="saved" stroke="#10b981" strokeWidth={2} fill="url(#gSaved)" name="节省" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* 7-day comparison — always visible */}
      {(() => {
        const weekRaw = chartData.reduce((s, d) => s + d.raw, 0);
        const weekSent = chartData.reduce((s, d) => s + d.sent, 0);
        const weekSaved = chartData.reduce((s, d) => s + d.saved, 0);
        const weekRate = weekRaw > 0 ? Math.min(weekSaved / weekRaw, 1.0) : (weekSaved > 0 ? 1.0 : 0);
        const hasData = chartData.length > 0;
        return (
          <div className="card-panel p-5">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h4 className="text-sm font-bold text-slate-800">七日 Token 消耗对比</h4>
                <p className="text-[10px] text-slate-400">原始消耗 vs 优化后实际发送 (近 7 日)</p>
              </div>
              {hasData && (
                <div className="flex gap-6 text-right">
                  <div>
                    <div className="text-[9px] text-slate-400 font-bold uppercase">原始总计</div>
                    <div className="text-lg font-mono font-bold text-slate-700">{formatNumber(weekRaw)}</div>
                  </div>
                  <div>
                    <div className="text-[9px] text-slate-400 font-bold uppercase">实际发送</div>
                    <div className="text-lg font-mono font-bold text-blue-600">{formatNumber(weekSent)}</div>
                  </div>
                  <div>
                    <div className="text-[9px] text-slate-400 font-bold uppercase">净节省</div>
                    <div className={cn('text-lg font-mono font-bold', weekSaved > 0 ? 'text-emerald-600' : 'text-slate-500')}>
                      {weekSaved > 0 ? '+' : ''}{formatNumber(weekSaved)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[9px] text-slate-400 font-bold uppercase">节省率</div>
                    <div className={cn('text-lg font-mono font-bold', weekRate > 0 ? 'text-emerald-600' : 'text-slate-500')}>
                      {weekRate > 0 ? `${(weekRate * 100).toFixed(1)}%` : '-'}
                    </div>
                  </div>
                </div>
              )}
            </div>
            {hasData ? (
              <>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} barCategoryGap="20%">
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                      <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} tickFormatter={(v: string) => v.slice(5)} />
                      <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} hide />
                      <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '11px' }} />
                      <Bar dataKey="raw" fill="#e2e8f0" radius={[3, 3, 0, 0]} name="原始消耗" />
                      <Bar dataKey="sent" fill="#3b82f6" radius={[3, 3, 0, 0]} name="实际发送" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-4 grid grid-cols-7 gap-2">
                  {chartData.map((d) => {
                    const pct = d.raw > 0 ? Math.min((d.saved / d.raw) * 100, 100) : 0;
                    return (
                      <div key={d.date} className="text-center">
                        <div className="text-[9px] text-slate-400 font-mono">{d.date.slice(5)}</div>
                        <div className="mt-1 mx-auto w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={cn('h-full rounded-full', pct > 0 ? 'bg-emerald-500' : 'bg-slate-300')}
                            style={{ width: `${Math.min(Math.max(pct, 0), 100)}%` }}
                          />
                        </div>
                        <div className={cn('text-[9px] font-bold mt-0.5', pct > 0 ? 'text-emerald-600' : 'text-slate-400')}>
                          {pct > 0 ? `${pct.toFixed(0)}%` : '-'}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-slate-400">
                <BarChart3 size={36} className="mb-2 text-slate-200" />
                <p className="text-xs font-medium">暂无 Token 数据</p>
                <p className="text-[10px] mt-1">通过 NexusGate 网关发送请求后，此处将展示七日消耗对比</p>
              </div>
            )}
          </div>
        );
      })()}

      {/* Recent traces table */}
      <div className="card-panel overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
          <h4 className="text-sm font-bold text-slate-800">最近请求</h4>
          <span className="text-[10px] text-slate-400">{traces.length} 条记录</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[10px] text-slate-400 font-bold uppercase border-b border-slate-100">
                <th className="text-left px-4 py-2">时间</th>
                <th className="text-left px-4 py-2">模型</th>
                <th className="text-right px-4 py-2">原始</th>
                <th className="text-right px-4 py-2">发送</th>
                <th className="text-right px-4 py-2">节省</th>
                <th className="text-right px-4 py-2">节省率</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {traces.slice(0, 20).map((tr, i) => {
                const ts = tr.token_stats;
                const raw = ts?.raw_input_tokens || ts?.estimated_prompt_tokens || 0;
                const sent = ts?.prompt_tokens || ts?.estimated_sent_tokens || 0;
                const saved = ts?.saved_tokens_actual || ts?.saved_tokens_estimated || 0;
                const rate = Math.min(Math.max(ts?.saved_rate_actual || ts?.saved_rate_estimated || 0, 0), 1.0);
                return (
                  <tr
                    key={i}
                    className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => setSelectedTrace(tr)}
                  >
                    <td className="px-4 py-2 font-mono text-slate-500">{tr.created_at ? new Date(tr.created_at * 1000).toLocaleTimeString('zh-CN') : '-'}</td>
                    <td className="px-4 py-2 font-mono text-slate-800">{tr.model || '-'}</td>
                    <td className="px-4 py-2 text-right font-mono">{formatNumber(raw)}</td>
                    <td className="px-4 py-2 text-right font-mono text-blue-600">{formatNumber(sent)}</td>
                    <td className="px-4 py-2 text-right font-mono text-emerald-600">{saved > 0 ? `+${formatNumber(saved)}` : '-'}</td>
                    <td className="px-4 py-2 text-right font-mono text-emerald-600">{rate > 0 ? `${(rate * 100).toFixed(0)}%` : '-'}</td>
                    <td className="px-4 py-2 text-right"><ChevronRight size={12} className="text-slate-300" /></td>
                  </tr>
                );
              })}
              {traces.length === 0 && !loading && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-400">暂无请求记录</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Trace detail modal */}
      <AnimatePresence>
        {selectedTrace && <TraceDetail trace={selectedTrace} onClose={() => setSelectedTrace(null)} />}
      </AnimatePresence>
    </motion.div>
  );
};
