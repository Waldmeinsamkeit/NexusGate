import { useState, useEffect } from 'react';
import { fetchHealth, type HealthResponse } from '../services/api';
import { cn } from '../lib/utils';

export const Header = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => {});
  }, []);

  return (
    <header className="h-12 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0 z-10">
      <div className="flex items-center gap-6 text-xs">
        <div className="flex flex-col">
          <span className="text-[9px] text-slate-400 uppercase font-bold">上游</span>
          <span className="font-mono text-slate-800 truncate max-w-[240px]">{health?.upstream || '-'}</span>
        </div>
        <div className="w-px h-5 bg-slate-200" />
        <div className="flex flex-col">
          <span className="text-[9px] text-slate-400 uppercase font-bold">模式</span>
          <span className="font-mono text-slate-600">{health?.upstream_mode || '-'}</span>
        </div>
      </div>
      <span className={cn(
        'flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border',
        health?.status === 'ok' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-slate-50 text-slate-500 border-slate-200',
      )}>
        <span className={cn('w-1.5 h-1.5 rounded-full', health?.status === 'ok' ? 'bg-emerald-500' : 'bg-slate-400')} />
        {health?.status === 'ok' ? 'READY' : 'OFFLINE'}
      </span>
    </header>
  );
};
