import React from 'react';
import { useTranslation } from 'react-i18next';
import { 
  LayoutDashboard, 
  Settings, 
  Database, 
  Activity, 
  Terminal, 
  Zap,
  ShieldCheck,
  ChevronRight,
  Menu,
  Box
} from 'lucide-react';
import { cn } from '../lib/utils';

interface NavItemProps {
  icon: React.ElementType;
  label: string;
  active?: boolean;
  onClick: () => void;
  key?: React.Key;
}

const NavItem = ({ icon: Icon, label, active, onClick }: NavItemProps) => {
  return (
    <button
      onClick={onClick}
      className={cn(
        "nav-item w-full text-left",
        active && "nav-item-active"
      )}
    >
      <Icon size={18} />
      <span>{label}</span>
      {active && <ChevronRight size={14} className="ml-auto text-brand-primary" />}
    </button>
  );
};

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Sidebar = ({ activeTab, setActiveTab }: SidebarProps) => {
  const { t } = useTranslation();
  
  const menuItems = [
    { id: 'dashboard', label: t('nav.dashboard'), icon: LayoutDashboard, category: 'Monitoring' },
    { id: 'traces', label: '请求追踪', icon: Activity, category: 'Monitoring' },
    { id: 'memory', label: t('nav.memCenter'), icon: Database, category: 'Knowledge' },
    { id: 'extraction', label: t('nav.extraction'), icon: Zap, category: 'Knowledge' },
    { id: 'pack', label: t('nav.memoryPack'), icon: Box, category: 'Knowledge' },
    { id: 'config', label: t('nav.upstreams'), icon: Settings, category: 'System' },
    { id: 'client', label: t('nav.clientAccess'), icon: Terminal, category: 'System' },
    { id: 'settings', label: t('nav.settings'), icon: ShieldCheck, category: 'System' },
  ];

  return (
    <aside className="w-60 bg-[#0F172A] text-slate-300 flex flex-col border-r border-slate-800 h-screen sticky top-0 shrink-0">
      <div className="p-6 border-b border-slate-800">
        <h1 className="text-white font-bold text-lg flex items-center gap-2">
          <span className="w-3 h-3 bg-blue-500 rounded-full shadow-[0_0_8px_#3B82F6]"></span>
          NexusGate <span className="text-[10px] bg-blue-900/50 text-blue-300 px-1.5 py-0.5 rounded border border-blue-700/50">v1.0.4</span>
        </h1>
      </div>
      
      <nav className="flex-1 py-4 overflow-y-auto no-scrollbar">
        <div className="px-4 mb-2 text-[10px] uppercase tracking-wider text-slate-500 font-bold italic">{t('nav.monitoring')}</div>
        {menuItems.filter(i => i.category === 'Monitoring').map((item) => (
          <NavItem
            key={item.id}
            icon={item.icon}
            label={item.label}
            active={activeTab === item.id}
            onClick={() => setActiveTab(item.id)}
          />
        ))}

        <div className="px-4 mt-6 mb-2 text-[10px] uppercase tracking-wider text-slate-500 font-bold italic">{t('nav.knowledge')}</div>
        {menuItems.filter(i => i.category === 'Knowledge').map((item) => (
          <NavItem
            key={item.id}
            icon={item.icon}
            label={item.label}
            active={activeTab === item.id}
            onClick={() => setActiveTab(item.id)}
          />
        ))}
        
        <div className="px-4 mt-6 mb-2 text-[10px] uppercase tracking-wider text-slate-500 font-bold italic">{t('nav.system')}</div>
        {menuItems.filter(i => i.category === 'System').map((item) => (
          <NavItem
            key={item.id}
            icon={item.icon}
            label={item.label}
            active={activeTab === item.id}
            onClick={() => setActiveTab(item.id)}
          />
        ))}
      </nav>
      
      <div className="p-4 border-t border-slate-800 text-[11px] text-slate-500">
        <div className="flex justify-between mb-1">
          <span>{t('common.uptime')}:</span>
          <span className="text-slate-300 font-mono italic">142h 12m</span>
        </div>
        <div className="flex justify-between">
          <span>{t('common.cpu')}:</span>
          <span className="text-emerald-400 font-mono">4.2%</span>
        </div>
      </div>
    </aside>
  );
};
