/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Dashboard } from './components/Dashboard';
import { MemoryCenter } from './components/MemoryCenter';
import { Settings } from './components/Settings';
import { ProviderManager } from './components/ProviderManager';
import { MemoryPackViewer } from './components/MemoryPackViewer';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [configVersion, setConfigVersion] = useState(0);
  const onConfigChanged = useCallback(() => setConfigVersion(v => v + 1), []);

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard': return <Dashboard />;
      case 'memory': return <MemoryCenter />;
      case 'mempack': return <MemoryPackViewer />;
      case 'settings': return <Settings onConfigChanged={onConfigChanged} />;
      case 'providers': return <ProviderManager configVersion={configVersion} onConfigChanged={onConfigChanged} />;
      default: return <Dashboard />;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#F8F9FA] text-[#1A1A1A] font-sans selection:bg-blue-500/30">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        
        <main className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="p-4">
            {renderContent()}
          </div>
        </main>
      </div>
    </div>
  );
}
