import React from 'react';
import { 
  Activity, 
  Terminal, 
  Globe, 
  Database, 
  RefreshCw, 
  CheckCircle2, 
  Sparkles,
  ExternalLink
} from 'lucide-react';
import { CitationSource, ChapterOutline } from '../types';
import { Language, translations } from '../locales/translations';

interface BentoRadarDashboardProps {
  logs: string[];
  citations: CitationSource[];
  outline: ChapterOutline[];
  criticFeedback?: string;
  currentStep: string;
  iterationCount: number;
  maxIterations: number;
  currentLang?: Language;
}

export const BentoRadarDashboard: React.FC<BentoRadarDashboardProps> = ({
  logs,
  citations,
  outline,
  criticFeedback,
  currentStep,
  iterationCount,
  maxIterations,
  currentLang = 'zh'
}) => {
  const t = translations[currentLang].radar;

  const allExtractedFacts = outline.flatMap((ch) => 
    (ch.extracted_facts || []).map(f => ({ chapter: ch.chapter_num, fact: f }))
  );

  return (
    <div className="max-w-7xl mx-auto w-full py-6 px-4 sm:px-6 space-y-6">
      
      {/* 头部状态条 */}
      <div className="theme-surface rounded-2xl p-5 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center animate-pulse">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base sm:text-lg font-bold">{t.title}</h2>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
            </div>
            <p className="text-xs opacity-70">{t.subtitle}</p>
          </div>
        </div>

        {/* 迭代轮次徽章 */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl theme-card text-xs font-mono border border-subtle">
            <RefreshCw className="w-3.5 h-3.5 text-blue-500 animate-spin" />
            <span>
              {t.round
                .replace('{current}', String(iterationCount || 1))
                .replace('{max}', String(maxIterations || 2))}
            </span>
          </div>
        </div>
      </div>

      {/* 三栏 Bento Grid 仪表盘 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* 1. 思考流终端 */}
        <div className="theme-surface rounded-2xl p-5 shadow-lg flex flex-col h-[520px]">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-subtle">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 theme-accent-text" />
              <h3 className="text-xs font-bold uppercase tracking-wider">{t.tabThought}</h3>
            </div>
            <span className="text-[10px] font-mono opacity-50">STDOUT</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 font-mono text-xs pr-1">
            {logs.length === 0 ? (
              <div className="text-xs opacity-50 italic py-8 text-center">
                {t.emptyThought}
              </div>
            ) : (
              logs.map((log, idx) => (
                <div
                  key={idx}
                  className="p-2 rounded-lg theme-nested text-[11px] leading-relaxed break-all animate-in fade-in"
                >
                  <span className="text-blue-500 mr-1.5">›</span>
                  <span className="opacity-90">{log}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 2. 网页抓取矩阵 */}
        <div className="theme-surface rounded-2xl p-5 shadow-lg flex flex-col h-[520px]">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-subtle">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-emerald-500" />
              <h3 className="text-xs font-bold uppercase tracking-wider">{t.tabScrape}</h3>
            </div>
            <span className="text-[10px] font-mono text-emerald-500">
              {t.sourceCitations.replace('{count}', String(citations.length))}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
            {citations.length === 0 ? (
              <div className="text-xs opacity-50 italic py-8 text-center">
                {t.emptyScrape}
              </div>
            ) : (
              citations.map((c, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl theme-card space-y-1.5 group hover:border-blue-500/40 transition"
                >
                  <div className="flex items-center justify-between">
                    <span className="w-5 h-5 rounded theme-nested font-mono text-[10px] font-bold flex items-center justify-center">
                      {c.id}
                    </span>
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-blue-500 hover:underline flex items-center gap-1 truncate max-w-[140px]"
                    >
                      <span>{new URL(c.url || 'http://web').hostname.replace('www.', '')}</span>
                      <ExternalLink className="w-2.5 h-2.5" />
                    </a>
                  </div>

                  <h4 className="text-xs font-semibold line-clamp-1 group-hover:text-blue-500 transition">
                    {c.title}
                  </h4>

                  <p className="text-[11px] opacity-75 line-clamp-2 leading-relaxed">
                    {c.snippet}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 3. 事实卡片瀑布流 & Critic 评估 */}
        <div className="theme-surface rounded-2xl p-5 shadow-lg flex flex-col h-[520px]">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-subtle">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-purple-500" />
              <h3 className="text-xs font-bold uppercase tracking-wider">{t.tabFacts}</h3>
            </div>
            <span className="text-[10px] font-mono text-purple-500">
              {allExtractedFacts.length} Facts
            </span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
            {/* Critic 实时反馈卡片 */}
            {criticFeedback && (
              <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 space-y-1.5">
                <div className="flex items-center justify-between text-[11px] text-purple-500 font-semibold">
                  <div className="flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{t.criticHeader}</span>
                  </div>
                  <span className="px-1.5 py-0.5 rounded-full bg-purple-500/20 text-[9px]">
                    {t.passBadge}
                  </span>
                </div>
                <p className="text-xs opacity-90 leading-relaxed">
                  {criticFeedback}
                </p>
              </div>
            )}

            {allExtractedFacts.length === 0 ? (
              <div className="text-xs opacity-50 italic py-8 text-center">
                {t.emptyFacts}
              </div>
            ) : (
              allExtractedFacts.map((item, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl theme-nested space-y-1 text-xs leading-relaxed animate-in fade-in"
                >
                  <div className="flex items-center gap-1.5 text-[10px] opacity-60 font-mono">
                    <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                    <span>Chapter 0{item.chapter}</span>
                  </div>
                  <p className="opacity-90">{item.fact}</p>
                </div>
              ))
            )}
          </div>
        </div>

      </div>

    </div>
  );
};
