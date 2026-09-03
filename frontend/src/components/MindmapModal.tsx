import React, { useState, useMemo } from 'react';
import { X, Network, ChevronRight, ChevronDown, Sparkles, Layers, BookOpen, FileText, Download } from 'lucide-react';
import { ChapterOutline } from '../types';
import { Language, translations } from '../locales/translations';
import { downloadBlob } from '../lib/utils';

interface MindmapModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: string;
  outline: ChapterOutline[];
  topic: string;
  currentLang?: Language;
}

interface MindNode {
  id: string;
  title: string;
  level: number;
  children: MindNode[];
}

export const MindmapModal: React.FC<MindmapModalProps> = ({
  isOpen,
  onClose,
  report,
  outline,
  topic,
  currentLang = 'zh'
}) => {
  const t = translations[currentLang].mindmap;
  const [collapsedNodes, setCollapsedNodes] = useState<Record<string, boolean>>({});

  const rootNode = useMemo<MindNode>(() => {
    const root: MindNode = {
      id: 'root',
      title: topic || (currentLang === 'zh' ? '深度研究课题全景' : 'Panoramic Research Graph'),
      level: 0,
      children: []
    };

    const lines = report.split('\n');
    let currentH1: MindNode | null = null;
    let currentH2: MindNode | null = null;

    lines.forEach((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) return;

      if (trimmed.startsWith('# ') && !trimmed.startsWith('## ')) {
        const title = trimmed.replace(/^#\s+/, '').replace(/\*\*/g, '');
        currentH1 = {
          id: `h1_${idx}`,
          title,
          level: 1,
          children: []
        };
        root.children.push(currentH1);
        currentH2 = null;
      } else if (trimmed.startsWith('## ') && !trimmed.startsWith('### ')) {
        const title = trimmed.replace(/^##\s+/, '').replace(/\*\*/g, '');
        currentH2 = {
          id: `h2_${idx}`,
          title,
          level: 2,
          children: []
        };
        if (currentH1) {
          currentH1.children.push(currentH2);
        } else {
          root.children.push(currentH2);
        }
      } else if (trimmed.startsWith('### ') || trimmed.startsWith('#### ') || trimmed.startsWith('- ') || /^\d+\.\s/.test(trimmed)) {
        const title = trimmed.replace(/^(#{3,4}\s+|[-*]\s+|\d+\.\s+)/, '').replace(/\*\*/g, '');
        if (title.length > 2 && title.length < 80) {
          const leaf: MindNode = {
            id: `leaf_${idx}`,
            title: title.slice(0, 50) + (title.length > 50 ? '...' : ''),
            level: 3,
            children: []
          };
          if (currentH2) {
            currentH2.children.push(leaf);
          } else if (currentH1) {
            currentH1.children.push(leaf);
          }
        }
      }
    });

    if (root.children.length === 0 && outline && outline.length > 0) {
      root.children = outline.map((ch, i) => ({
        id: `outline_${i}`,
        title: `${currentLang === 'zh' ? '第' : 'Ch'} ${ch.chapter_num} ${currentLang === 'zh' ? '章' : ''}: ${ch.title}`,
        level: 1,
        children: (ch.extracted_facts || []).slice(0, 3).map((f, fIdx) => ({
          id: `fact_${i}_${fIdx}`,
          title: f.slice(0, 35) + '...',
          level: 2,
          children: []
        }))
      }));
    }

    return root;
  }, [report, outline, topic, currentLang]);

  if (!isOpen) return null;

  const toggleCollapse = (id: string) => {
    setCollapsedNodes(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleExportJson = () => {
    const blob = new Blob([JSON.stringify(rootNode, null, 2)], { type: 'application/json' });
    const cleanTopic = (topic || '深度调研思维导图').replace(/[^\w\u4e00-\u9fa5]+/g, '_');
    downloadBlob(blob, `${cleanTopic}_mindmap.json`);
  };

  const renderNode = (node: MindNode) => {
    const isCollapsed = collapsedNodes[node.id];
    const hasChildren = node.children && node.children.length > 0;

    return (
      <div key={node.id} className="relative pl-6 py-1.5 border-l-2 border-subtle/60 ml-3">
        <div className="flex items-center gap-2 group">
          {hasChildren && (
            <button
              type="button"
              onClick={() => toggleCollapse(node.id)}
              aria-label={isCollapsed ? `Expand ${node.title}` : `Collapse ${node.title}`}
              className="w-4 h-4 rounded theme-nested flex items-center justify-center opacity-70 hover:opacity-100 cursor-pointer"
            >
              {isCollapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          )}

          <div
            className={`px-3 py-1.5 rounded-xl transition shadow-sm flex items-center gap-2 max-w-xl ${
              node.level === 0
                ? 'theme-btn-primary text-white font-bold text-sm'
                : node.level === 1
                ? 'theme-card font-semibold text-xs border-l-4 border-l-blue-500'
                : node.level === 2
                ? 'theme-nested text-xs font-medium'
                : 'bg-black/5 dark:bg-white/5 text-[11px] opacity-85'
            }`}
          >
            {node.level === 0 ? (
              <Sparkles className="w-4 h-4 shrink-0" />
            ) : node.level === 1 ? (
              <BookOpen className="w-3.5 h-3.5 theme-accent-text shrink-0" />
            ) : node.level === 2 ? (
              <Layers className="w-3 h-3 opacity-60 shrink-0" />
            ) : (
              <FileText className="w-2.5 h-2.5 opacity-40 shrink-0" />
            )}
            <span className="leading-snug">{node.title}</span>
            {hasChildren && (
              <span className="text-[10px] opacity-50 font-mono px-1.5 py-0.2 rounded-full theme-nested">
                {node.children.length}
              </span>
            )}
          </div>
        </div>

        {hasChildren && !isCollapsed && (
          <div className="mt-1 space-y-1">
            {node.children.map(renderNode)}
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="mindmap-modal-title"
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
    >
      <div className="theme-surface rounded-3xl w-full max-w-4xl h-[85vh] p-6 shadow-2xl flex flex-col space-y-4">
        
        {/* 头部 */}
        <div className="flex items-center justify-between border-b border-subtle pb-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl theme-btn-primary flex items-center justify-center text-white">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <h3 id="mindmap-modal-title" className="text-base font-bold">{t.title}</h3>
              <p className="text-xs opacity-70">{t.subtitle}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleExportJson}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl theme-card text-xs font-medium opacity-90 hover:opacity-100 transition cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 theme-accent-text" />
              <span>{t.exportJsonBtn}</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close mindmap modal"
              className="opacity-70 hover:opacity-100 p-1.5 rounded-lg theme-nested transition cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 思维导图画布 */}
        <div className="flex-1 overflow-auto p-4 rounded-2xl theme-nested border border-subtle">
          <div className="min-w-fit">
            {renderNode(rootNode)}
          </div>
        </div>

        {/* 底部操作 */}
        <div className="flex items-center justify-between pt-2 border-t border-subtle text-xs">
          <span className="opacity-70 font-sans">{t.tip}</span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 theme-btn-primary rounded-xl font-medium cursor-pointer"
          >
            {t.close}
          </button>
        </div>

      </div>
    </div>
  );
};
