import React from 'react';
import {
  LayoutDashboard,
  Settings,
  Database,
  ArrowRightLeft,
  Package,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../lib/utils';

const NavItem: React.FC<{ icon: React.ElementType; label: string; active?: boolean; onClick: () => void }> = ({ icon: Icon, label, active, onClick }) => (
  <button
    onClick={onClick}
    className={cn('nav-item w-full text-left', active && 'nav-item-active')}
  >
    <Icon size={18} />
    <span>{label}</span>
    {active && <ChevronRight size={14} className="ml-auto text-brand-primary" />}
  </button>
);

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Sidebar = ({ activeTab, setActiveTab }: SidebarProps) => {
  const items = [
    { id: 'dashboard', label: '看板', icon: LayoutDashboard },
    { id: 'memory', label: '记忆工作台', icon: Database },
    { id: 'mempack', label: 'Memory Pack', icon: Package },
    { id: 'settings', label: '系统设置', icon: Settings },
    { id: 'providers', label: '上游管理', icon: ArrowRightLeft },
  ];

  return (
    <aside className="w-60 bg-[#0F172A] text-slate-300 flex flex-col border-r border-slate-800 h-screen sticky top-0 shrink-0">
      <div className="p-6 border-b border-slate-800">
        <h1 className="text-white font-bold text-lg flex items-center gap-2">
          <span className="w-3 h-3 bg-blue-500 rounded-full shadow-[0_0_8px_#3B82F6]"></span>
          NexusGate
        </h1>
      </div>

      <nav className="flex-1 py-4 overflow-y-auto no-scrollbar">
        {items.map((item) => (
          <NavItem
            key={item.id}
            icon={item.icon}
            label={item.label}
            active={activeTab === item.id}
            onClick={() => setActiveTab(item.id)}
          />
        ))}
      </nav>
    </aside>
  );
};
