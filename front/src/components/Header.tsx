import { useTranslation } from 'react-i18next';
import { Settings, ShieldCheck } from 'lucide-react';

export const Header = () => {
  const { t } = useTranslation();

  /**
   * BACKEND INTEGRATION POINT:
   * Fetch the current active upstream provider, base URL, and overall gateway health status.
   * Endpoint: GET /api/v1/status/active-gateway
   */

  return (
    <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0 z-10">
      <div className="flex items-center gap-8">
        <div className="flex flex-col">
          <span className="text-[10px] text-slate-400 uppercase font-bold tracking-tight">{t('header.provider')}</span>
          <span className="text-xs font-semibold text-slate-800">OpenRouter (DeepSeek-V3)</span>
        </div>
        <div className="w-px h-6 bg-slate-200"></div>
        <div className="flex flex-col">
          <span className="text-[10px] text-slate-400 uppercase font-bold tracking-tight">{t('header.baseUrl')}</span>
          <span className="text-xs font-mono text-blue-600 truncate max-w-[200px]">https://api.openrouter.ai/v1</span>
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-full text-[11px] font-bold">
          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span> {t('header.status')}: {t('header.ready')}
        </div>
        
        <button className="p-1.5 hover:bg-slate-100 rounded-md text-slate-500 transition-colors">
          <Settings size={18} />
        </button>
      </div>
    </header>
  );
};
