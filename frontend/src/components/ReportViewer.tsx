import React, { useState, useMemo, useRef, useEffect } from 'react';
import { 
  Download, 
  Copy, 
  Check, 
  MessageSquare, 
  List, 
  Sparkles, 
  ShieldCheck,
  Network
} from 'lucide-react';
import { CitationSource, ChapterOutline } from '../types';
import { CitationPopover } from './CitationPopover';
import { Language, translations } from '../locales/translations';

interface ReportViewerProps {
  report: string;
  citations: CitationSource[];
  outline?: ChapterOutline[];
  onOpenQA: (initialQuery?: string) => void;
  onOpenExport: () => void;
  onOpenMindmap?: () => void;
  onDeepDive?: (text: string) => void;
  currentLang?: Language;
}

// 跨浏览器/跨协议兼容的通用复制函数
async function copyTextToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (e) {
      console.warn('Clipboard API failed, trying fallback:', e);
    }
  }

  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';
  textArea.style.left = '-999999px';
  textArea.style.top = '-999999px';
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  try {
    const success = document.execCommand('copy');
    textArea.remove();
    return success;
  } catch (err) {
    console.error('Fallback copy failed:', err);
    textArea.remove();
    return false;
  }
}

export const ReportViewer: React.FC<ReportViewerProps> = ({
  report,
  citations,
  outline,
  onOpenQA,
  onOpenExport,
  onOpenMindmap,
  onDeepDive,
  currentLang = 'zh'
}) => {
  const t = translations[currentLang].report;
  const [copied, setCopied] = useState(false);
  const [activeCitation, setActiveCitation] = useState<CitationSource | null>(null);
  const [isPinned, setIsPinned] = useState(false);
  const [popoverPos, setPopoverPos] = useState({ x: 0, y: 0 });
  const [selectedText, setSelectedText] = useState('');
  const [selectionPos, setSelectionPos] = useState<{ x: number; y: number } | null>(null);
  const [activeHeadingId, setActiveHeadingId] = useState<string>('');
  const closeTimerRef = useRef<any>(null);

  // 提取 TOC 目录 (支持 1~4 级标题)
  const toc = useMemo(() => {
    const headings: { level: number; text: string; id: string }[] = [];
    const lines = report.split('\n');
    lines.forEach((line) => {
      const match = line.match(/^(#{1,4})\s+(.+)$/);
      if (match) {
        const level = match[1].length;
        const text = match[2].replace(/\[\d+\]/g, '').replace(/\*\*/g, '').trim();
        const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
        headings.push({ level, text, id });
      }
    });
    return headings;
  }, [report]);

  // 滚动监听 (Scroll-Spy)
  useEffect(() => {
    const handleScroll = () => {
      const headingElements = toc
        .map(h => document.getElementById(h.id))
        .filter(Boolean) as HTMLElement[];

      const scrollPos = window.scrollY + 140;
      let currentId = '';

      for (const el of headingElements) {
        if (el.offsetTop <= scrollPos) {
          currentId = el.id;
        } else {
          break;
        }
      }

      if (currentId) {
        setActiveHeadingId(currentId);
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [toc]);

  const handleCopy = async () => {
    const ok = await copyTextToClipboard(report);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } else {
      alert(currentLang === 'zh' ? '复制失败，请手动划选文本复制' : 'Copy failed, please select text manually');
    }
  };

  const handleCitationMouseEnter = (e: React.MouseEvent, id: number) => {
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    const rect = e.currentTarget.getBoundingClientRect();
    const found = citations.find(c => c.id === id);
    if (found) {
      setActiveCitation(found);
      setPopoverPos({ x: rect.left + rect.width / 2, y: rect.bottom });
    }
  };

  const handleCitationMouseLeave = () => {
    if (isPinned) return;
    closeTimerRef.current = setTimeout(() => {
      setActiveCitation(null);
    }, 450);
  };

  const handlePopoverMouseEnter = () => {
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
  };

  const handlePopoverMouseLeave = () => {
    if (isPinned) return;
    closeTimerRef.current = setTimeout(() => {
      setActiveCitation(null);
    }, 350);
  };

  const handleCitationClick = (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    const rect = e.currentTarget.getBoundingClientRect();
    const found = citations.find(c => c.id === id);
    if (found) {
      if (activeCitation?.id === id && isPinned) {
        setActiveCitation(null);
        setIsPinned(false);
      } else {
        setActiveCitation(found);
        setIsPinned(true);
        setPopoverPos({ x: rect.left + rect.width / 2, y: rect.bottom });
      }
    }
  };

  const handleMouseUp = () => {
    const selection = window.getSelection();
    if (selection && selection.toString().trim().length >= 3) {
      const text = selection.toString().trim();
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      
      if (rect.width > 0 && rect.height > 0) {
        setSelectedText(text);
        setSelectionPos({
          x: Math.max(80, Math.min(rect.left + rect.width / 2, window.innerWidth - 120)),
          y: Math.max(10, rect.top - 42)
        });
        return;
      }
    }
    setSelectionPos(null);
  };

  const handleTocClick = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    const el = document.getElementById(id);
    if (el) {
      const yOffset = -80;
      const y = el.getBoundingClientRect().top + window.pageYOffset + yOffset;
      window.scrollTo({ top: y, behavior: 'smooth' });
      setActiveHeadingId(id);
    }
  };

  // 行内元素解析
  const parseInlineMarkdown = (text: string): React.ReactNode[] => {
    if (!text) return [];

    const regex = /(\*\*.*?\*\*|`.*?`|\[\d+\])/g;
    const parts = text.split(regex);

    return parts.map((part, index) => {
      if (!part) return null;

      if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
        return (
          <strong key={index} className="font-bold text-inherit opacity-100">
            {parseInlineMarkdown(part.slice(2, -2))}
          </strong>
        );
      }

      if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
        return (
          <code key={index} className="theme-nested px-1.5 py-0.5 rounded text-xs font-mono theme-accent-text">
            {part.slice(1, -1)}
          </code>
        );
      }

      const citationMatch = part.match(/^\[(\d+)\]$/);
      if (citationMatch) {
        const cid = parseInt(citationMatch[1], 10);
        return (
          <button
            key={index}
            type="button"
            className="citation-badge"
            onMouseEnter={(e) => handleCitationMouseEnter(e, cid)}
            onMouseLeave={handleCitationMouseLeave}
            onClick={(e) => handleCitationClick(e, cid)}
            title={t.pinHint}
          >
            {cid}
          </button>
        );
      }

      return <span key={index}>{part}</span>;
    });
  };

  // 块级元素解析 (全面支持 h1, h2, h3, h4, h5, table, ul, blockquote)
  const renderFormattedMarkdown = (content: string) => {
    const blocks = content.split('\n\n');
    return blocks.map((block, bIdx) => {
      const trimmed = block.trim();
      if (!trimmed) return null;

      // 1. 标题 1 (# ...)
      if (trimmed.startsWith('# ')) {
        const title = trimmed.replace(/^#\s+/, '');
        const id = title.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
        return (
          <h1 key={bIdx} id={id} className="text-2xl sm:text-3xl font-extrabold mt-8 mb-4 pb-2 border-b border-subtle leading-tight scroll-mt-24">
            {parseInlineMarkdown(title)}
          </h1>
        );
      }

      // 2. 标题 2 (## ...)
      if (trimmed.startsWith('## ')) {
        const title = trimmed.replace(/^##\s+/, '');
        const id = title.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
        return (
          <h2 key={bIdx} id={id} className="text-xl sm:text-2xl font-bold mt-7 mb-3 flex items-center gap-2 leading-snug scroll-mt-24">
            <span className="w-1.5 h-5 theme-accent-bg rounded-full shrink-0" />
            <span>{parseInlineMarkdown(title)}</span>
          </h2>
        );
      }

      // 3. 标题 3 (### ...)
      if (trimmed.startsWith('### ')) {
        const title = trimmed.replace(/^###\s+/, '');
        const id = title.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
        return (
          <h3 key={bIdx} id={id} className="text-base sm:text-lg font-semibold theme-accent-text mt-5 mb-2 scroll-mt-24">
            {parseInlineMarkdown(title)}
          </h3>
        );
      }

      // 4. 标题 4 (#### ...)
      if (trimmed.startsWith('#### ')) {
        const title = trimmed.replace(/^####\s+/, '');
        const id = title.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
        return (
          <h4 key={bIdx} id={id} className="text-sm sm:text-base font-bold opacity-90 mt-4 mb-2 scroll-mt-24">
            {parseInlineMarkdown(title)}
          </h4>
        );
      }

      // 5. 标题 5 (##### ...)
      if (trimmed.startsWith('##### ')) {
        const title = trimmed.replace(/^#####\s+/, '');
        return (
          <h5 key={bIdx} className="text-xs sm:text-sm font-semibold opacity-80 mt-3 mb-1">
            {parseInlineMarkdown(title)}
          </h5>
        );
      }

      // 6. Markdown 表格
      if (trimmed.includes('|') && trimmed.includes('\n|')) {
        const lines = trimmed.split('\n').filter(l => l.trim().startsWith('|'));
        if (lines.length >= 2) {
          const headerCells = lines[0].split('|').slice(1, -1).map(c => c.trim());
          const rowLines = lines.slice(2);

          return (
            <div key={bIdx} className="my-5 overflow-x-auto rounded-xl border border-subtle">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="theme-nested border-b border-subtle">
                    {headerCells.map((h, hIdx) => (
                      <th key={hIdx} className="p-3 font-semibold">
                        {parseInlineMarkdown(h)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-subtle">
                  {rowLines.map((row, rIdx) => {
                    const cells = row.split('|').slice(1, -1).map(c => c.trim());
                    return (
                      <tr key={rIdx} className="hover:bg-slate-500/5 transition">
                        {cells.map((cell, cIdx) => (
                          <td key={cIdx} className="p-3 opacity-90 leading-relaxed">
                            {parseInlineMarkdown(cell)}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        }
      }

      // 7. 列表
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || /^\d+\.\s/.test(trimmed)) {
        const items = trimmed.split('\n');
        return (
          <ul key={bIdx} className="space-y-2 my-3 pl-4 border-l-2 border-subtle">
            {items.map((item, iIdx) => {
              const cleanItem = item.replace(/^([-*]|\d+\.)\s+/, '');
              return (
                <li key={iIdx} className="text-sm leading-relaxed opacity-90">
                  {parseInlineMarkdown(cleanItem)}
                </li>
              );
            })}
          </ul>
        );
      }

      // 8. 引用块
      if (trimmed.startsWith('>')) {
        const quoteText = trimmed.replace(/^>\s*/gm, '');
        return (
          <blockquote key={bIdx} className="my-4 p-3.5 pl-4 rounded-r-xl border-l-4 border-accent theme-nested italic text-sm opacity-90 leading-relaxed">
            {parseInlineMarkdown(quoteText)}
          </blockquote>
        );
      }

      // 9. 段落 (支持段落内部包含 #### 或多行解析)
      const subLines = trimmed.split('\n');
      if (subLines.length > 1 && subLines.some(l => l.startsWith('#### ') || l.startsWith('### '))) {
        return (
          <div key={bIdx} className="my-3 space-y-2">
            {subLines.map((line, lIdx) => {
              const lTrim = line.trim();
              if (lTrim.startsWith('#### ')) {
                return (
                  <h4 key={lIdx} className="text-sm font-bold opacity-95 mt-3 mb-1">
                    {parseInlineMarkdown(lTrim.replace(/^####\s+/, ''))}
                  </h4>
                );
              }
              if (lTrim.startsWith('### ')) {
                return (
                  <h3 key={lIdx} className="text-base font-semibold theme-accent-text mt-3 mb-1">
                    {parseInlineMarkdown(lTrim.replace(/^###\s+/, ''))}
                  </h3>
                );
              }
              return (
                <p key={lIdx} className="text-sm leading-relaxed opacity-90">
                  {parseInlineMarkdown(lTrim)}
                </p>
              );
            })}
          </div>
        );
      }

      return (
        <p key={bIdx} className="text-sm sm:text-base leading-relaxed my-3.5 opacity-90">
          {parseInlineMarkdown(trimmed)}
        </p>
      );
    });
  };

  return (
    <div 
      className="max-w-7xl mx-auto w-full py-6 px-4 sm:px-6 relative" 
      onMouseUp={handleMouseUp}
      onClick={() => {
        if (isPinned) {
          setIsPinned(false);
          setActiveCitation(null);
        }
      }}
    >
      
      {/* 悬浮/固定引用卡片 */}
      {activeCitation && (
        <CitationPopover
          citation={activeCitation}
          position={popoverPos}
          currentLang={currentLang}
          onClose={() => {
            setActiveCitation(null);
            setIsPinned(false);
          }}
          onMouseEnter={handlePopoverMouseEnter}
          onMouseLeave={handlePopoverMouseLeave}
        />
      )}

      {/* 划词深挖悬浮按钮 */}
      {selectionPos && (
        <div
          style={{
            top: `${selectionPos.y}px`,
            left: `${selectionPos.x - 70}px`
          }}
          className="fixed z-50 theme-btn-primary text-white text-xs font-semibold px-3 py-1.5 rounded-full shadow-2xl flex items-center gap-1.5 hover:brightness-110 cursor-pointer animate-in fade-in select-none"
          onMouseDown={(e) => {
            e.stopPropagation();
            if (onDeepDive && selectedText) {
              onDeepDive(selectedText);
            } else {
              onOpenQA(`${currentLang === 'zh' ? '请结合研报，重点深入解析这一论述' : 'Please deep dive into this excerpt'}: "${selectedText}"`);
            }
            setSelectionPos(null);
          }}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>{t.deepDiveTooltip}</span>
        </div>
      )}

      {/* 顶部操作工具栏 */}
      <div className="theme-surface rounded-2xl p-4 mb-6 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold">{t.badgeTitle}</div>
            <div className="text-xs opacity-70">
              {t.badgeSubtitle.replace('{count}', String(citations.length))}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onOpenMindmap && (
            <button
              type="button"
              onClick={onOpenMindmap}
              className="px-3.5 py-2 theme-card text-xs font-medium rounded-xl flex items-center gap-1.5 transition cursor-pointer"
            >
              <Network className="w-3.5 h-3.5 theme-accent-text" />
              <span>{t.mindmapBtn}</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleCopy}
            className="px-3.5 py-2 theme-card text-xs font-medium rounded-xl flex items-center gap-1.5 transition cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? t.copied : t.copyFull}</span>
          </button>

          <button
            type="button"
            onClick={onOpenExport}
            className="px-3.5 py-2 theme-card text-xs font-medium rounded-xl flex items-center gap-1.5 transition cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 theme-accent-text" />
            <span>{t.exportReport}</span>
          </button>

          <button
            type="button"
            onClick={() => onOpenQA()}
            className="px-4 py-2 theme-btn-primary text-xs font-semibold rounded-xl shadow-lg flex items-center gap-1.5 transition cursor-pointer"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>{t.liveQABtn}</span>
          </button>
        </div>
      </div>

      {/* 主体两栏 */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start relative">
        
        {/* 左侧真吸顶目录 */}
        <aside className="hidden lg:block lg:col-span-1 sticky top-20 z-10 self-start">
          <div className="theme-surface rounded-2xl p-4 space-y-3 max-h-[calc(100vh-6.5rem)] overflow-y-auto shadow-lg border border-subtle">
            <div className="flex items-center gap-2 text-xs font-bold pb-2 border-b border-subtle">
              <List className="w-4 h-4 theme-accent-text" />
              <span>{t.tocTitle}</span>
            </div>
            <nav className="space-y-1 text-xs">
              {toc.map((item, idx) => {
                const isCurrent = activeHeadingId === item.id;
                return (
                  <a
                    key={idx}
                    href={`#${item.id}`}
                    onClick={(e) => handleTocClick(e, item.id)}
                    className={`block py-1.5 px-2.5 rounded-lg transition truncate ${
                      isCurrent
                        ? 'theme-pill-active font-semibold shadow-sm'
                        : 'opacity-70 hover:opacity-100 hover:theme-nested'
                    } ${
                      item.level === 1 ? 'font-medium' : item.level === 2 ? 'pl-4 text-xs' : item.level === 3 ? 'pl-6 text-[11px]' : 'pl-8 text-[10px]'
                    }`}
                  >
                    {item.text}
                  </a>
                );
              })}
            </nav>
          </div>
        </aside>

        {/* 右侧研报正文卡片 */}
        <div className="lg:col-span-3">
          <article className="theme-surface rounded-3xl p-6 sm:p-10 shadow-2xl prose-custom select-text">
            {renderFormattedMarkdown(report)}
          </article>
        </div>

      </div>

    </div>
  );
};
