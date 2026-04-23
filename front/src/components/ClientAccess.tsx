import { 
  Terminal, 
  Copy, 
  Check, 
  Code2, 
  Box, 
  Cpu, 
  Layers,
  ChevronRight
} from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'motion/react';

const CodeBlock = ({ code, language }: { code: string, language: string }) => {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      <div className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={copy} className="p-1.5 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 text-slate-300">
          {copied ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
        </button>
      </div>
      <div className="text-[10px] font-bold text-slate-500 uppercase bg-slate-900 px-4 py-1.5 border-b border-slate-800 rounded-t-xl flex justify-between items-center">
        <span>{language}</span>
      </div>
      <pre className="bg-slate-950 p-4 rounded-b-xl border border-t-0 border-slate-800 overflow-x-auto custom-scrollbar">
        <code className="text-xs font-mono text-slate-300 leading-relaxed">{code}</code>
      </pre>
    </div>
  );
};

export const ClientAccess = () => {
  const { t } = useTranslation();
  const scripts = {
    openai: `import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "YOUR_NEXUSGATE_KEY",
  baseURL: "https://nexus-gate.internal/v1",
});

const response = await client.chat.completions.create({
  model: "gpt-4o",
  messages: [{ role: "user", content: "Hello!" }],
});`,
    curl: `curl https://nexus-gate.internal/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_NEXUSGATE_KEY" \\
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "How's the memory state?"}]
  }'`,
    aider: `aider --openai-api-key YOUR_NEXUSGATE_KEY \\
      --openai-api-base https://nexus-gate.internal/v1 \\
      --model gpt-4o`,
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <header className="flex justify-between items-center bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-800">{t('client.title')}</h2>
          <p className="text-slate-400 text-[11px] font-medium uppercase tracking-tight">{t('client.subtitle')}</p>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-8 h-8 bg-blue-50 text-blue-600 rounded flex items-center justify-center border border-blue-100">
            <Box size={16} />
          </div>
          <div>
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">{t('client.baseUrl')}</div>
            <div className="text-xs font-mono font-bold text-slate-700">nexus-gate.internal/v1</div>
          </div>
        </div>
        <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-8 h-8 bg-indigo-50 text-indigo-600 rounded flex items-center justify-center border border-indigo-100">
            <Layers size={16} />
          </div>
          <div>
            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">{t('client.version')}</div>
            <div className="text-xs font-bold text-indigo-600 uppercase tracking-widest">v1.2.4-stable</div>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <section className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex items-center gap-3">
            <div className="w-5 h-5 rounded-full bg-slate-800 text-white flex items-center justify-center text-[10px] font-bold">1</div>
            <h3 className="text-xs font-bold uppercase tracking-wide text-slate-700">OpenAI SDK (Node.js/Python)</h3>
          </div>
          <CodeBlock code={scripts.openai} language="typescript" />
        </section>

        <section className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex items-center gap-3">
            <div className="w-5 h-5 rounded-full bg-slate-800 text-white flex items-center justify-center text-[10px] font-bold">2</div>
            <h3 className="text-xs font-bold uppercase tracking-wide text-slate-700">直接 API 调用 (curl)</h3>
          </div>
          <CodeBlock code={scripts.curl} language="bash" />
        </section>

        <div className="p-6 bg-[#0F172A] text-white rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Terminal size={32} className="text-blue-400" />
            <div>
              <div className="font-bold text-sm">{t('client.docsTitle')}</div>
              <div className="text-xs text-slate-400">{t('client.docsSubtitle')}</div>
            </div>
          </div>
          <button className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-lg font-bold text-xs border border-slate-700 flex items-center gap-2 transition-colors">
            {t('client.readDocs')}
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </motion.div>
  );
};
