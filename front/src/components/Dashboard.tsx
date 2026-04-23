import { useTranslation } from 'react-i18next';
import { cn } from '../lib/utils';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  AreaChart, 
  Area 
} from 'recharts';
import { Zap, Activity, Database, Shield, Server, Box, ArrowUpRight, TrendingUp } from 'lucide-react';
import { mockStats } from '../services/mockData';
import { formatNumber, formatPercent } from '../lib/utils';
import { motion } from 'motion/react';

const StatCard = ({ title, value, subtext, trend, colorClass }: any) => (
  <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
    <h3 className="text-[10px] text-slate-400 font-bold uppercase mb-1 tracking-wider">{title}</h3>
    <div className="flex items-end justify-between">
      <span className={cn("text-2xl font-mono font-bold tracking-tight", colorClass || "text-slate-800")}>{value}</span>
      {trend && (
        <span className={cn("text-xs font-bold mb-1", trend.startsWith('+') ? "text-emerald-500" : "text-rose-500")}>
          {trend}
        </span>
      )}
      {subtext && !trend && (
        <span className="text-slate-400 text-[10px] mb-1 font-medium">{subtext}</span>
      )}
    </div>
  </div>
);

export const Dashboard = () => {
  const { t } = useTranslation();
  
  /**
   * BACKEND INTEGRATION POINT:
   * Fetch aggregated usage statistics for the dashboard.
   * Endpoint: GET /api/v1/stats/summary
   * Response: { totalTokens: number, savedTokens: number, fallbacks: number, trimCount: number, etc. }
   */
  const stats = mockStats; // Replace with actual API call

  /**
   * BACKEND INTEGRATION POINT:
   * Fetch historical token usage and savings data.
   * Endpoint: GET /api/v1/stats/trends?days=7
   */
  const chartData = [
    { name: '04/16', original: 1200, actual: 960, saved: 240, cache: 140, trim: 100 },
    { name: '04/17', original: 2400, actual: 1820, saved: 580, cache: 350, trim: 230 },
    { name: '04/18', original: 2000, actual: 1580, saved: 420, cache: 280, trim: 140 },
    { name: '04/19', original: 3100, actual: 2150, saved: 950, cache: 600, trim: 350 },
    { name: '04/20', original: 2700, actual: 1980, saved: 720, cache: 450, trim: 270 },
    { name: '04/21', original: 3500, actual: 2400, saved: 1100, cache: 750, trim: 350 },
    { name: '04/22', original: 3200, actual: 2220, saved: 980, cache: 650, trim: 330 },
  ];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard 
          title="原始预估消耗" 
          value={formatNumber(18100)} 
          trend="+14.2%"
          subtext="不使用本程序时"
        />
        <StatCard 
          title="节省后实际消耗" 
          value={formatNumber(13110)} 
          colorClass="text-blue-600"
          subtext="优化后发送至上游"
        />
        <StatCard 
          title="累计节省 Token" 
          value={formatNumber(4990)} 
          colorClass="text-emerald-600"
          subtext="27.6% 节省率"
        />
        <StatCard 
          title={t('dashboard.trimCount')} 
          value="182" 
          colorClass="text-indigo-600"
          subtext="平均缩减 18%"
        />
        <StatCard 
          title={t('dashboard.rewriteCount')} 
          value="64" 
          colorClass="text-emerald-600"
          subtext="安全合规重写"
        />
        <StatCard 
          title={t('dashboard.latency')} 
          value={`${mockStats.avgLatency}ms`} 
          trend="+42ms"
        />
      </div>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 space-y-4">
          <div className="bg-white border border-slate-200 p-5 rounded-lg flex flex-col min-h-[400px] shadow-sm">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h4 className="text-sm font-bold flex items-center gap-2 italic font-serif text-slate-800 mb-1">
                  {t('dashboard.trend')}
                </h4>
                <p className="text-[10px] text-slate-400 font-medium">近 7 日优化效率对比 (Tokens)</p>
              </div>
              <div className="flex flex-col items-end gap-2">
                <div className="flex gap-4">
                  <span className="flex items-center gap-1.5 text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                    <span className="w-2 h-2 bg-slate-300 rounded-sm"></span> 不使用本程序
                  </span>
                  <span className="flex items-center gap-1.5 text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                    <span className="w-2 h-2 bg-blue-500 rounded-sm shadow-[0_0_8px_rgba(59,130,246,0.5)]"></span> 节省后消耗
                  </span>
                </div>
                <div className="px-2 py-0.5 bg-blue-50 border border-blue-100 rounded text-[9px] text-blue-600 font-bold flex items-center gap-1">
                   <TrendingUp size={10} /> 节省效率提升 4.2%
                </div>
              </div>
            </div>
            <div className="flex-1 h-[250px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorOriginal" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f1f5f9" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#f1f5f9" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} hide />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '11px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="original" 
                    stroke="#cbd5e1" 
                    fill="url(#colorOriginal)" 
                    name="不使用本程序" 
                  />
                  <Area 
                    type="monotone" 
                    dataKey="actual" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    fill="url(#colorActual)" 
                    name="节省后消耗" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 grid grid-cols-2 lg:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-lg border border-slate-100">
               <div className="space-y-1">
                  <div className="text-[9px] font-bold text-slate-400">主要节省驱动</div>
                  <div className="text-[11px] font-bold text-slate-700">元规则存储击中 (Memory Hit)</div>
                  <div className="h-1 w-full bg-slate-200 rounded-full overflow-hidden">
                     <div className="h-full bg-blue-500 w-[65%]"></div>
                  </div>
               </div>
               <div className="space-y-1">
                  <div className="text-[9px] font-bold text-slate-400">上下文裁剪</div>
                  <div className="text-[11px] font-bold text-slate-700 text-emerald-600">减少 327k 冗余</div>
                  <div className="h-1 w-full bg-slate-200 rounded-full overflow-hidden">
                     <div className="h-full bg-emerald-500 w-[42%]"></div>
                  </div>
               </div>
               <div className="space-y-1">
                  <div className="text-[9px] font-bold text-slate-400">并发抑制</div>
                  <div className="text-[11px] font-bold text-slate-700">防抖节省 5%</div>
                  <div className="h-1 w-full bg-slate-200 rounded-full overflow-hidden">
                     <div className="h-full bg-slate-400 w-[15%]"></div>
                  </div>
               </div>
               <div className="space-y-1">
                  <div className="text-[9px] font-bold text-slate-400">Token 单价估算</div>
                  <div className="text-[11px] font-bold text-slate-700 font-mono text-blue-600">≈ $124.50 Saved</div>
                  <div className="h-1 w-full bg-slate-200 rounded-full overflow-hidden">
                     <div className="h-full bg-amber-400 w-[80%] shadow-[0_0_4px_#fbbf24]"></div>
                  </div>
               </div>
            </div>

            <div className="mt-6 border-t border-slate-100 pt-5">
              <div className="flex items-start justify-between mb-4 px-1">
                <div>
                  <h5 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">近 7 日 Token 节省额度对比</h5>
                  <p className="text-[9px] text-slate-400">展示每日成功拦截并省下的 Token 总量</p>
                </div>
                <div className="flex gap-3">
                  <span className="flex items-center gap-1 text-[9px] font-bold text-slate-400 uppercase">
                    <span className="w-1.5 h-1.5 bg-slate-200 rounded-full"></span> 原始预计
                  </span>
                  <span className="flex items-center gap-1 text-[9px] font-bold text-emerald-500 uppercase">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span> 净节省量
                  </span>
                </div>
              </div>
              
              <div className="h-[120px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="colorOriginalSmall" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#e2e8f0" stopOpacity={0.1}/>
                        <stop offset="95%" stopColor="#e2e8f0" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorSavedSmall" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.1}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis 
                      dataKey="name" 
                      fontSize={9} 
                      axisLine={false} 
                      tickLine={false} 
                      stroke="#94a3b8" 
                      tick={{ dy: 5 }}
                    />
                    <YAxis hide />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '4px', fontSize: '10px' }}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="original" 
                      stroke="#cbd5e1" 
                      strokeWidth={1.5}
                      fill="url(#colorOriginalSmall)" 
                      name="原始预计消耗" 
                    />
                    <Area 
                      type="monotone" 
                      dataKey="saved" 
                      stroke="#10b981" 
                      strokeWidth={2}
                      fill="url(#colorSavedSmall)" 
                      name="净节省 Token" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <hr className="border-slate-100 my-6" />

          <div className="grid grid-cols-1 gap-4 pb-8">
            <div className="bg-[#0F172A] text-white rounded-lg p-6 relative overflow-hidden flex flex-col justify-center shadow-lg min-h-[220px]">
              <div className="absolute top-0 right-0 p-6">
                 <div className="w-16 h-16 border-2 border-blue-500/30 rounded-full flex items-center justify-center">
                   <div className="w-10 h-10 border border-blue-500/50 rounded-full animate-pulse"></div>
                 </div>
              </div>
              <div className="max-w-2xl">
                <h4 className="text-[10px] font-bold uppercase text-blue-400 mb-1 tracking-widest">接地验证健康度 (Grounding Health)</h4>
                <div className="text-4xl font-mono font-bold uppercase mb-2">0.12<span className="text-[11px] font-sans text-slate-400 ml-3 font-normal tracking-normal">平均幻觉比率 (Hallucination Rate)</span></div>
                <p className="text-[12px] text-slate-400 mb-6 font-medium italic">基于最近 1,000 次推理生成的交叉验证审计结果 · 实时环境稳定性：极高</p>
                <div className="mt-auto">
                  <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                     <div className="h-full bg-blue-500 w-[12%] shadow-[0_0_15px_rgba(59,130,246,0.8)]"></div>
                  </div>
                  <div className="flex justify-between items-center mt-3">
                    <div className="text-[11px] text-slate-400 uppercase tracking-wider font-bold italic flex items-center gap-2">
                       <Shield size={12} className="text-blue-500" />
                       当前状态: 环境置信度稳定
                    </div>
                    <div className="text-[10px] text-blue-400 font-bold border border-blue-500/30 px-2 py-0.5 rounded">
                      HEALTHY
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
