import React, { useState, useMemo, useRef, useEffect } from 'react';
import { 
  Download, 
  Copy, 
  Check, 
  MessageSquare, 
  List, 
  Sparkles, 
  ShieldCheck,
  Network,
  FileText,
  ExternalLink,
  Headphones,
  Play,
  Pause,
  RotateCcw,
  Volume2,
  Loader2,
  Presentation,
  FileImage,
  BookOpen,
  Radio,
  GitFork,
  MessageSquareQuote
} from 'lucide-react';
import { CitationSource, ChapterOutline } from '../types';
import { CitationPopover } from './CitationPopover';
import { MermaidDiagram } from './MermaidDiagram';
import { MathFormula } from './MathFormula';
import { Language, translations } from '../locales/translations';
import { slugifyHeading, splitMarkdownBlocks, copyToClipboard } from '../lib/utils';
import { getAudioSummaryUrl, getLivePresentationUrl } from '../lib/api';
import { PresentationModal } from './PresentationModal';
import { GlossaryPopover } from './GlossaryPopover';
import { InfographicCard } from './InfographicCard';
import { PodcastPlayer } from './PodcastPlayer';
import { CausalMindmapModal } from './CausalMindmapModal';
import { SocialQuotesModal } from './SocialQuotesModal';
import { NLIRadarModal } from './NLIRadarModal';

interface ReportViewerProps {
  report: string;
  citations: CitationSource[];
  outline?: ChapterOutline[];
  taskId?: string;
  onOpenQA: (initialQuery?: string) => void;
  onOpenExport: () => void;
  onOpenMindmap?: () => void;
  onDeepDive?: (text: string) => void;
  currentLang?: Language;
  currentTheme?: string;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({
  report,
  citations,
  outline,
  taskId,
  onOpenQA,
  onOpenExport,
  onOpenMindmap,
  onDeepDive,
  currentLang = 'zh',
  currentTheme = 'vintage'
}) => {
  const t = translations[currentLang].report;
  const [copied, setCopied] = useState(false);
  const [activeCitation, setActiveCitation] = useState<CitationSource | null>(null);
  const [isPinned, setIsPinned] = useState(false);
  const [popoverPos, setPopoverPos] = useState({ x: 0, y: 0 });
  const [selectedText, setSelectedText] = useState('');
  const [selectionPos, setSelectionPos] = useState<{ x: number; y: number } | null>(null);
  const [activeHeadingId, setActiveHeadingId] = useState<string>('');
  const [isPresentationModalOpen, setIsPresentationModalOpen] = useState(false);
  const [isInfographicOpen, setIsInfographicOpen] = useState(false);
  const [isPodcastModalOpen, setIsPodcastModalOpen] = useState(false);
  const [isCausalMindmapOpen, setIsCausalMindmapOpen] = useState(false);
  const [isSocialQuotesOpen, setIsSocialQuotesOpen] = useState(false);
  const [isNLIRadarOpen, setIsNLIRadarOpen] = useState(false);
  const [selectedContext, setSelectedContext] = useState('');
  const [glossaryTerm, setGlossaryTerm] = useState('');
  const [glossaryContext, setGlossaryContext] = useState('');
  const [glossaryPos, setGlossaryPos] = useState<{ x: number; y: number } | null>(null);
  const closeTimerRef = useRef<any>(null);

  const reportTitle = useMemo(() => {
    const firstH1 = report.split('\n').find(l => l.startsWith('# '));
    if (firstH1) return firstH1.replace(/^#\s+/, '').replace(/[*#]/g, '').trim();
    return outline?.[0]?.title || '前沿深度研究报告';
  }, [report, outline]);

  // Edge-TTS 音频播客播放器状态
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [audioProgress, setAudioProgress] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [audioCurrentTime, setAudioCurrentTime] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [audioError, setAudioError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const formatAudioTime = (secs: number) => {
    if (isNaN(secs) || secs < 0) return '00:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleToggleAudio = () => {
    if (!audioRef.current) return;
    setAudioError(null);

    // 若尚未加载 src，则设置后端音频接口
    if (!audioRef.current.src || audioRef.current.src === window.location.href) {
      if (!taskId) {
        setAudioError('未找到任务标识，无法获取音频');
        return;
      }
      setIsLoadingAudio(true);
      audioRef.current.src = getAudioSummaryUrl(taskId);
      audioRef.current.load();
    }

    if (isPlayingAudio) {
      audioRef.current.pause();
      setIsPlayingAudio(false);
    } else {
      audioRef.current.play().then(() => {
        setIsPlayingAudio(true);
        setIsLoadingAudio(false);
      }).catch((e) => {
        console.error('Audio play failed:', e);
        setIsLoadingAudio(false);
        setIsPlayingAudio(false);
        setAudioError(t.podcastError || '音频加载失败');
      });
    }
  };

  const handleSeekAudio = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!audioRef.current || !audioDuration) return;
    const newPercent = parseFloat(e.target.value);
    const newTime = (newPercent / 100) * audioDuration;
    audioRef.current.currentTime = newTime;
    setAudioCurrentTime(newTime);
    setAudioProgress(newPercent);
  };

  const handleCycleSpeed = () => {
    const speeds = [1.0, 1.25, 1.5, 0.75];
    const nextIdx = (speeds.indexOf(playbackSpeed) + 1) % speeds.length;
    const nextSpeed = speeds[nextIdx];
    setPlaybackSpeed(nextSpeed);
    if (audioRef.current) {
      audioRef.current.playbackRate = nextSpeed;
    }
  };

  // 提取 TOC 目录 (支持 1~4 级标题，使用共享 slugifyHeading - Bug 21)
  const toc = useMemo(() => {
    const headings: { level: number; text: string; id: string }[] = [];
    const lines = report.split('\n');
    let headingIndex = 0;
    lines.forEach((line) => {
      const match = line.match(/^(#{1,4})\s+(.+)$/);
      if (match) {
        const level = match[1].length;
        const text = match[2].replace(/\[\^cite:\d+\]/g, '').replace(/\[\d+\]/g, '').replace(/\*\*/g, '').trim();
        const id = slugifyHeading(text, headingIndex++);
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
    const ok = await copyToClipboard(report);
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
    if (selection && selection.toString().trim().length >= 2) {
      const text = selection.toString().trim();
      try {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        
        if (rect.width > 0 && rect.height > 0) {
          setSelectedText(text);
          const parentEl = range.startContainer.parentElement;
          setSelectedContext(parentEl?.textContent || text);
          setSelectionPos({
            x: Math.max(80, Math.min(rect.left + rect.width / 2, window.innerWidth - 140)),
            y: Math.max(10, rect.top - 46)
          });
          return;
        }
      } catch (e) {}
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

  // 行内元素解析 (支持 **粗体**、`代码`、LaTeX 公式、Markdown 链接 [文本](url)、[^cite:N]、[^N] 以及 [N] 角标)
  const parseInlineMarkdown = (text: string): React.ReactNode[] => {
    if (!text) return [];

    const regex = /(\*\*.*?\*\*|`.*?`|\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$|\\\(.*?\\\)|\$[^\$\n]+\$|\[\^cite:\d+\]|\[\^\d+\]|\[\d+\]|\[[^\]]+\]\([^\)]+\))/g;
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

      // Markdown 链接与本地专有文档格式 [linkText](url)
      const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) {
        const linkText = linkMatch[1];
        const linkUrl = linkMatch[2];
        if (linkUrl.startsWith('local://')) {
          const fname = linkUrl.replace('local://', '');
          return (
            <span
              key={index}
              className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium text-xs border border-emerald-500/25 shadow-xs"
              title={`本地私有 RAG 专有文档: ${fname}`}
            >
              <FileText className="w-3.5 h-3.5 shrink-0" />
              <span>{linkText}</span>
            </span>
          );
        }
        return (
          <a
            key={index}
            href={linkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1 font-medium transition cursor-pointer"
            title={linkUrl}
          >
            <span>{linkText}</span>
            <ExternalLink className="w-3 h-3 opacity-60 shrink-0" />
          </a>
        );
      }

      // 行内 LaTeX 块级/行内公式
      if (
        (part.startsWith('\\[') && part.endsWith('\\]')) ||
        (part.startsWith('$$') && part.endsWith('$$'))
      ) {
        return <MathFormula key={index} formula={part} displayMode={true} />;
      }
      if (
        (part.startsWith('\\(') && part.endsWith('\\)')) ||
        (part.startsWith('$') && part.endsWith('$') && part.length >= 2)
      ) {
        return <MathFormula key={index} formula={part} displayMode={false} />;
      }

      const citeTokenMatch = part.match(/^\[\^cite:(\d+)\]$/) || part.match(/^\[\^(\d+)\]$/) || part.match(/^\[(\d+)\]$/);
      if (citeTokenMatch) {
        const cid = parseInt(citeTokenMatch[1], 10);
        return (
          <button
            key={index}
            type="button"
            className="citation-badge"
            aria-label={`Citation [${cid}]`}
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

  // 块级元素解析 (全面支持 h1, h2, h3, h4, h5, table, ul, blockquote, LaTeX, Mermaid)
  const renderFormattedMarkdown = (content: string) => {
    const blocks = splitMarkdownBlocks(content);
    let headingCount = 0;
    return blocks.map((block, bIdx) => {
      const trimmed = block.trim();
      if (!trimmed) return null;

      try {
        // 0. Mermaid 图表渲染 (支持 ```mermaid 围栏代码块及裸各类 Mermaid 图表声明语法)
      const isMermaid = 
        trimmed.toLowerCase().startsWith('```mermaid') ||
        (trimmed.startsWith('```') && (
          trimmed.includes('graph ') || 
          trimmed.includes('flowchart ') || 
          trimmed.includes('subgraph') || 
          trimmed.includes('gantt') || 
          trimmed.includes('sequenceDiagram') ||
          trimmed.includes('mindmap') ||
          trimmed.includes('classDiagram') ||
          trimmed.includes('stateDiagram') ||
          trimmed.includes('pie') ||
          trimmed.includes('erDiagram') ||
          trimmed.includes('journey') ||
          trimmed.includes('gitGraph')
        )) ||
        trimmed.startsWith('graph ') ||
        trimmed.startsWith('flowchart ') ||
        trimmed.startsWith('subgraph') ||
        trimmed.startsWith('sequenceDiagram') ||
        trimmed.startsWith('gantt') ||
        trimmed.startsWith('mindmap') ||
        trimmed.startsWith('classDiagram') ||
        trimmed.startsWith('stateDiagram') ||
        trimmed.startsWith('pie') ||
        trimmed.startsWith('erDiagram') ||
        trimmed.startsWith('journey') ||
        trimmed.startsWith('quadrantChart') ||
        trimmed.startsWith('gitGraph') ||
        (trimmed.includes('subgraph') && trimmed.includes('-->') && trimmed.includes('end'));

      if (isMermaid) {
        return <MermaidDiagram key={bIdx} code={trimmed} theme={currentTheme} />;
      }

      // 0.1 常规代码块渲染
      if (trimmed.startsWith('```') && trimmed.endsWith('```')) {
        const codeContent = trimmed.replace(/^```[a-zA-Z]*\n?/, '').replace(/```$/, '').trim();
        return (
          <pre key={bIdx} className="my-4 p-4 rounded-xl theme-nested overflow-x-auto text-xs font-mono border border-subtle">
            <code>{codeContent}</code>
          </pre>
        );
      }

      // 0.2 LaTeX 块级独立公式 (\[ ... \] 或 $$ ... $$，允许末尾带标点符号)
      const isDisplayMath = 
        (trimmed.startsWith('\\[') && /\\\]\s*[,.]?$/.test(trimmed)) ||
        (trimmed.startsWith('$$') && /\$\$\s*[,.]?$/.test(trimmed));

      if (isDisplayMath) {
        const cleanFormula = trimmed.replace(/\s*[,.]?$/, '');
        return <MathFormula key={bIdx} formula={cleanFormula} displayMode={true} />;
      }

      // 1. 标题 1 (# ...)
      if (trimmed.startsWith('# ') && !trimmed.startsWith('## ')) {
        const title = trimmed.replace(/^#\s+/, '');
        const id = slugifyHeading(title, headingCount++);
        return (
          <h1 key={bIdx} id={id} className="text-2xl sm:text-3xl font-extrabold mt-8 mb-4 pb-2 border-b border-subtle leading-tight scroll-mt-24">
            {parseInlineMarkdown(title)}
          </h1>
        );
      }

      // 2. 标题 2 (## ...)
      if (trimmed.startsWith('## ') && !trimmed.startsWith('### ')) {
        const title = trimmed.replace(/^##\s+/, '');
        const id = slugifyHeading(title, headingCount++);
        return (
          <h2 key={bIdx} id={id} className="text-xl sm:text-2xl font-bold mt-7 mb-3 flex items-center gap-2 leading-snug scroll-mt-24">
            <span className="w-1.5 h-5 theme-accent-bg rounded-full shrink-0" />
            <span>{parseInlineMarkdown(title)}</span>
          </h2>
        );
      }

      // 3. 标题 3 (### ...)
      if (trimmed.startsWith('### ') && !trimmed.startsWith('#### ')) {
        const title = trimmed.replace(/^###\s+/, '');
        const id = slugifyHeading(title, headingCount++);
        return (
          <h3 key={bIdx} id={id} className="text-base sm:text-lg font-semibold theme-accent-text mt-5 mb-2 scroll-mt-24">
            {parseInlineMarkdown(title)}
          </h3>
        );
      }

      // 4. 标题 4 (#### ...)
      if (trimmed.startsWith('#### ') && !trimmed.startsWith('##### ')) {
        const title = trimmed.replace(/^####\s+/, '');
        const id = slugifyHeading(title, headingCount++);
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

      // 7. 列表与参考文献卡片结构化解析
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || /^\d+\.\s/.test(trimmed)) {
        // 智能重组列表行：将缩进的 > 引证块合并为当前列表项的 quote 字段，杜绝拆成孤立的第二个圆点列表项
        const rawLines = trimmed.split('\n');
        const listItems: { main: string; quote?: string }[] = [];
        let curItem: { main: string; quote?: string } | null = null;

        for (const rawLine of rawLines) {
          const isNewItem = /^(\s{0,3})([-*]|\d+\.)\s+/.test(rawLine);
          if (isNewItem) {
            if (curItem) listItems.push(curItem);
            const cleanContent = rawLine.replace(/^(\s{0,3})([-*]|\d+\.)\s+/, '');
            curItem = { main: cleanContent };
          } else if (curItem) {
            const trimmedLine = rawLine.trim();
            if (trimmedLine.startsWith('>')) {
              const quoteContent = trimmedLine.replace(/^>\s*/, '').replace(/^["“]|["”]$/g, '');
              curItem.quote = (curItem.quote ? curItem.quote + ' ' : '') + quoteContent;
            } else {
              curItem.main += ' ' + trimmedLine;
            }
          } else {
            curItem = { main: rawLine.trim() };
          }
        }
        if (curItem) listItems.push(curItem);

        return (
          <div key={bIdx} className="space-y-3 my-4">
            {listItems.map((item, iIdx) => {
              // 匹配参考文献引证项格式：[1] 或 **[1]**
              const citeMatch = item.main.match(/^(?:\*\*\[(\d+)\]\*\*|\[(\d+)\])\s*(.*)$/);
              if (citeMatch) {
                const cid = citeMatch[1] || citeMatch[2];
                const restContent = citeMatch[3];
                return (
                  <div key={iIdx} className="p-4 rounded-xl theme-card border border-subtle space-y-2.5 shadow-xs transition hover:border-blue-500/40">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="w-5 h-5 rounded-full bg-blue-500/15 text-blue-600 dark:text-blue-400 font-mono text-xs font-bold flex items-center justify-center shrink-0 border border-blue-500/30 shadow-xs">
                        {cid}
                      </span>
                      <div className="text-sm font-semibold flex-1">
                        {parseInlineMarkdown(restContent)}
                      </div>
                    </div>
                    {item.quote && (
                      <div className="pl-7 text-xs opacity-80 italic border-l-2 border-blue-500/40 leading-relaxed font-sans">
                        “{item.quote}”
                      </div>
                    )}
                  </div>
                );
              }

              return (
                <div key={iIdx} className="flex items-start gap-2.5 text-sm leading-relaxed opacity-90 pl-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-2 shrink-0 opacity-70" />
                  <div className="flex-1 space-y-1">
                    <div>{parseInlineMarkdown(item.main)}</div>
                    {item.quote && (
                      <div className="pl-3 text-xs opacity-75 italic border-l-2 border-subtle my-1">
                        “{item.quote}”
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
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
      } catch (err) {
        console.error(`Block render error at index ${bIdx}:`, err);
        return (
          <p key={bIdx} className="text-sm sm:text-base leading-relaxed my-3.5 opacity-90">
            {trimmed}
          </p>
        );
      }
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

      {/* 划词悬浮胶囊：释义 + 深挖 */}
      {selectionPos && (
        <div
          style={{
            top: `${selectionPos.y}px`,
            left: `${Math.max(16, selectionPos.x - 110)}px`
          }}
          className="fixed z-50 bg-slate-900/95 border border-cyan-500/40 text-white text-xs font-semibold p-1 rounded-full shadow-2xl flex items-center gap-1 backdrop-blur-md animate-in fade-in select-none"
        >
          {selectedText.length <= 35 && (
            <button
              type="button"
              onMouseDown={(e) => {
                e.stopPropagation();
                setGlossaryTerm(selectedText);
                setGlossaryContext(selectedContext);
                setGlossaryPos(selectionPos);
                setSelectionPos(null);
              }}
              className="px-2.5 py-1 rounded-full bg-cyan-500/20 hover:bg-cyan-500/40 text-cyan-300 flex items-center gap-1 transition cursor-pointer"
            >
              <BookOpen className="w-3 h-3" />
              <span>划词释义</span>
            </button>
          )}

          <button
            type="button"
            onMouseDown={(e) => {
              e.stopPropagation();
              if (onDeepDive && selectedText) {
                onDeepDive(selectedText);
              } else {
                onOpenQA(`${currentLang === 'zh' ? '请结合研报，重点深入解析这一论述' : 'Please deep dive into this excerpt'}: "${selectedText}"`);
              }
              setSelectionPos(null);
            }}
            className="px-2.5 py-1 rounded-full bg-blue-600 hover:bg-blue-500 text-white flex items-center gap-1 transition cursor-pointer"
          >
            <Sparkles className="w-3 h-3 text-amber-300" />
            <span>{t.deepDiveTooltip}</span>
          </button>
        </div>
      )}

      {/* 顶部操作工具栏 */}
      <div className="theme-surface rounded-2xl p-4 mb-6 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div 
          onClick={() => setIsNLIRadarOpen(true)}
          className="flex items-center gap-3 cursor-pointer hover:opacity-85 transition group"
          title="点击查看文献 NLI 语义蕴含裁判与抗幻觉雷达"
        >
          <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 group-hover:scale-105 transition">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold flex items-center gap-1.5">
              <span>{t.badgeTitle}</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                🛡️ NLI 96%+
              </span>
            </div>
            <div className="text-xs opacity-70">
              {t.badgeSubtitle.replace('{count}', String(citations.length))} · 点击核验雷达
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* 双角色对谈播客 */}
          {taskId && (
            <button
              type="button"
              onClick={() => setIsPodcastModalOpen(true)}
              className="px-3.5 py-2 theme-card text-xs font-medium rounded-xl flex items-center gap-1.5 transition cursor-pointer hover:border-purple-500/50"
              title="NotebookLM 级双主持人（云希+晓晓）生动对谈播客"
            >
              <Radio className="w-3.5 h-3.5 text-purple-400 animate-pulse" />
              <span>双人播客</span>
            </button>
          )}

          {/* 因果脑图 */}
          <button
            type="button"
            onClick={() => setIsCausalMindmapOpen(true)}
            className="px-3.5 py-2 theme-card text-xs font-medium rounded-xl flex items-center gap-1.5 transition cursor-pointer hover:border-cyan-500/50"
            title="因果机制与方案权衡知识图谱思维导图"
          >
            <GitFork className="w-3.5 h-3.5 text-cyan-400" />
            <span>因果脑图</span>
          </button>

          {/* 社交金句 */}
          <button
            type="button"
            onClick={() => setIsSocialQuotesOpen(true)}
            className="px-3.5 py-2 theme-card text-xs font-medium rounded-xl flex items-center gap-1.5 transition cursor-pointer hover:border-rose-500/50"
            title="提炼社交爆款认知金句与 𝕏/即刻/小红书文案"
          >
            <MessageSquareQuote className="w-3.5 h-3.5 text-rose-400" />
            <span>社交金句</span>
          </button>

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
            onClick={() => setIsInfographicOpen(true)}
            className="px-3.5 py-2 theme-card text-xs font-medium rounded-xl flex items-center gap-1.5 transition cursor-pointer hover:border-cyan-500/50"
            title="生成并导出 2x 超清社交高光快报海报 (PNG)"
          >
            <FileImage className="w-3.5 h-3.5 text-cyan-500" />
            <span>社交长图</span>
          </button>

          {taskId && (
            <button
              type="button"
              onClick={() => setIsPresentationModalOpen(true)}
              className="px-3.5 py-2 theme-card text-xs font-medium rounded-xl flex items-center gap-1.5 transition cursor-pointer hover:border-blue-500/50"
              title="在浏览器中以 16:9 全屏模式直接放映幻灯片"
            >
              <Presentation className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              <span>全屏演示</span>
            </button>
          )}

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

      {/* 隐藏的 HTML5 原生 Audio 标签 */}
      <audio
        ref={audioRef}
        onTimeUpdate={() => {
          if (audioRef.current) {
            const cur = audioRef.current.currentTime;
            const dur = audioRef.current.duration || 0;
            setAudioCurrentTime(cur);
            setAudioDuration(dur);
            if (dur > 0) setAudioProgress((cur / dur) * 100);
          }
        }}
        onLoadedMetadata={() => {
          if (audioRef.current) {
            setAudioDuration(audioRef.current.duration || 0);
            setIsLoadingAudio(false);
          }
        }}
        onEnded={() => {
          setIsPlayingAudio(false);
          setAudioProgress(0);
          setAudioCurrentTime(0);
        }}
        onError={() => {
          setIsLoadingAudio(false);
          setIsPlayingAudio(false);
          setAudioError(t.podcastError || '音频加载异常，请稍后重试');
        }}
      />

      {/* 🎧 Edge-TTS 异步研报播客速听栏 */}
      <div className="theme-surface rounded-2xl p-4 mb-6 shadow-xl border border-blue-500/20 bg-gradient-to-r from-blue-500/5 via-indigo-500/5 to-purple-500/5 transition">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          
          {/* 左侧播客标识 */}
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition shadow-sm ${
              isPlayingAudio 
                ? 'bg-blue-600 text-white animate-pulse shadow-blue-500/30' 
                : 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20'
            }`}>
              <Headphones className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold flex items-center gap-2">
                <span>{t.podcastTitle}</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/30">
                  Microsoft Neural
                </span>
              </div>
              <div className="text-xs opacity-70">
                {audioError ? (
                  <span className="text-red-500 font-medium">{audioError}</span>
                ) : (
                  <span>沉浸式聆听研报核心洞察 · 云希专业播报</span>
                )}
              </div>
            </div>
          </div>

          {/* 中间播放控制与进度条 */}
          <div className="flex items-center gap-3 w-full sm:flex-1 max-w-md">
            <button
              type="button"
              onClick={handleToggleAudio}
              disabled={isLoadingAudio}
              aria-label={isPlayingAudio ? t.podcastPause : t.podcastPlay}
              className="w-9 h-9 rounded-full bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center shrink-0 shadow-md transition cursor-pointer disabled:opacity-50"
            >
              {isLoadingAudio ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : isPlayingAudio ? (
                <Pause className="w-4 h-4 fill-current" />
              ) : (
                <Play className="w-4 h-4 fill-current ml-0.5" />
              )}
            </button>

            <span className="text-xs font-mono opacity-80 shrink-0 select-none">
              {formatAudioTime(audioCurrentTime)} / {formatAudioTime(audioDuration)}
            </span>

            {/* 可拖拽进度条 */}
            <input
              type="range"
              min="0"
              max="100"
              step="0.1"
              value={isNaN(audioProgress) ? 0 : audioProgress}
              onChange={handleSeekAudio}
              className="flex-1 h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-blue-600 focus:outline-none"
            />
          </div>

          {/* 右侧倍速调节与下载 */}
          <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
            <button
              type="button"
              onClick={handleCycleSpeed}
              className="px-2.5 py-1.5 theme-card text-xs font-mono font-bold rounded-lg border border-subtle hover:border-blue-500/40 transition cursor-pointer"
              title={t.podcastSpeed}
            >
              {playbackSpeed.toFixed(2).replace(/\.00$/, '')}x
            </button>

            {taskId && (
              <a
                href={getAudioSummaryUrl(taskId)}
                download={`podcast_${taskId}.mp3`}
                className="p-1.5 theme-card text-xs rounded-lg border border-subtle hover:border-blue-500/40 opacity-75 hover:opacity-100 transition flex items-center justify-center cursor-pointer"
                title={t.podcastDownload}
              >
                <Download className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              </a>
            )}
          </div>

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

      {/* AI 演示文稿智能编排与动画弹窗 */}
      <PresentationModal
        isOpen={isPresentationModalOpen}
        onClose={() => setIsPresentationModalOpen(false)}
        taskId={taskId || ''}
        reportTitle={outline?.[0]?.title || '深度研究汇报演示'}
      />

      {/* 专有名词划词释义浮窗 */}
      {glossaryPos && (
        <GlossaryPopover
          term={glossaryTerm}
          context={glossaryContext}
          position={glossaryPos}
          onClose={() => setGlossaryPos(null)}
          onAskInQA={(q) => onOpenQA(q)}
        />
      )}

      {/* 社交高光快报长图卡片 */}
      <InfographicCard
        isOpen={isInfographicOpen}
        onClose={() => setIsInfographicOpen(false)}
        title={reportTitle}
        report={report}
        citations={citations}
        taskId={taskId}
      />

      {/* 阶段五：四大核心多模态交互弹窗 */}
      <PodcastPlayer
        taskId={taskId || 'default_task'}
        title={reportTitle}
        isOpen={isPodcastModalOpen}
        onClose={() => setIsPodcastModalOpen(false)}
      />

      <CausalMindmapModal
        taskId={taskId || 'default_task'}
        title={reportTitle}
        report={report}
        isOpen={isCausalMindmapOpen}
        onClose={() => setIsCausalMindmapOpen(false)}
      />

      <SocialQuotesModal
        taskId={taskId || 'default_task'}
        title={reportTitle}
        report={report}
        isOpen={isSocialQuotesOpen}
        onClose={() => setIsSocialQuotesOpen(false)}
      />

      <NLIRadarModal
        taskId={taskId || 'default_task'}
        title={reportTitle}
        report={report}
        citations={citations}
        isOpen={isNLIRadarOpen}
        onClose={() => setIsNLIRadarOpen(false)}
      />
    </div>
  );
};
