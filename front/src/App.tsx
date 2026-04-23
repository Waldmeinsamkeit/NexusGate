/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Dashboard } from './components/Dashboard';
import { UpstreamConfigView } from './components/UpstreamConfig';
import { MemoryCenter } from './components/MemoryCenter';
import { RequestTracing } from './components/RequestTracing';
import { SafetyGrounding } from './components/SafetyGrounding';
import { ClientAccess } from './components/ClientAccess';
import { MemoryPackPreview } from './components/MemoryPackPreview';
import { Settings } from './components/Settings';
import { MemoryExtraction } from './components/MemoryExtraction';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard': return <Dashboard />;
      case 'config': return <UpstreamConfigView />;
      case 'memory': return <MemoryCenter />;
      case 'traces': return <RequestTracing />;
      case 'extraction': return <MemoryExtraction />;
      case 'pack': return <MemoryPackPreview />;
      case 'safety': return <SafetyGrounding />;
      case 'client': return <ClientAccess />;
      case 'settings': return <Settings />;
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
