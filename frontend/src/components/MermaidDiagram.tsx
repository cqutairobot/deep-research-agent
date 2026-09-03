import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import mermaid from 'mermaid';
import { 
  Copy, 
  Check, 
  AlertCircle, 
  Maximize2, 
  Download, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw,
  X,
  Move
} from 'lucide-react';

interface MermaidDiagramProps {
  code: string;
  theme?: string;
}

export const cleanAndFormatMermaidCode = (rawCode: string): string => {
  let clean = rawCode.trim();
  
  // 1. 移除首尾可能存在的三反引号及单反引号
  clean = clean.replace(/^```[a-zA-Z]*\n?/, '').replace(/```$/, '').trim();
  clean = clean.replace(/^`+|`+$/g, '').trim();

  // 2. 全角中文箭头标准化为 ASCII 合法箭头（修复 --＞、==＞、-.-> 等输入法或误转换导致的所有语法错误）
  clean = clean.replace(/--+＞/g, '-->');
  clean = clean.replace(/==+＞/g, '==>');
  clean = clean.replace(/-\.+-＞/g, '-.->');
  clean = clean.replace(/＜--+/g, '<--');
  clean = clean.replace(/＜==+/g, '<==');

  // 3. 检查是否包含标准 Mermaid 图表声明头
  const hasHeader = /^(graph\s+[A-Za-z]+|flowchart\s+[A-Za-z]+|sequenceDiagram|gantt|classDiagram|stateDiagram|pie|erDiagram|journey|mindmap|quadrantChart)/i.test(clean);
  if (!hasHeader) {
    if (clean.includes('subgraph') || clean.includes('-->') || clean.includes('---')) {
      clean = 'graph TD\n' + clean;
    }
  }

  // 4. 修复同一行挤压的语句（仅匹配行内水平空格，彻底杜绝死循环）
  clean = clean.replace(/(\bend\b)[ \t]+(subgraph\b)/gi, '$1\n$2');
  clean = clean.replace(/(\])[ \t]+([A-Za-z0-9_]+\[)/g, '$1\n    $2');
  clean = clean.replace(/(\bend\b)[ \t]+([A-Za-z0-9_]+\s*-->)/gi, '$1\n    $2');
  clean = clean.replace(/(\b[A-Za-z0-9_]+\s*-->\s*[^ \t\r\n]+)[ \t]+(?=[A-Za-z0-9_]+\s*-->)/g, '$1\n    ');

  // 5. 仅在非箭头情况下，将裸 < 与 > 转换为安全字符（注意：绝不误伤 --> 或 ==>）
  clean = clean.replace(/<(?!--|==|[a-zA-Z\/])/g, '＜');
  clean = clean.replace(/(?<![-=.a-zA-Z])>/g, '＞');

  // 6. 逐行修复：截断标签、未闭合括号、末尾非代码文本清洗
  const lines = clean.split('\n');
  const fixedLines = lines.map(line => {
    let l = line.trimEnd();
    if (l.endsWith('<br') || l.endsWith('<br/')) {
      l = l.slice(0, l.lastIndexOf('<br'));
    }
    
    // 如果行末节点后紧跟附带的提示语/用户提问 (如 "H --> J你确定你改好了吗")，剥离非代码后缀
    l = l.replace(/(-->|==>|-\.->)\s*([A-Za-z0-9_]+)([\u4e00-\u9fa5\uff00-\uffef\s]+.*)$/, '$1 $2');

    const openBrackets = (l.match(/\[/g) || []).length;
    const closeBrackets = (l.match(/\]/g) || []).length;
    if (openBrackets > closeBrackets) {
      return l + ']'.repeat(openBrackets - closeBrackets);
    }
    return l;
  });
  clean = fixedLines.join('\n');

  // 7. 自动补全未闭合的 subgraph (避免漏写 end 导致语法报错)
  const subgraphMatches = clean.match(/\bsubgraph\b/g) || [];
  const endMatches = clean.match(/\bend\b/g) || [];
  if (subgraphMatches.length > endMatches.length) {
    clean += '\n' + '    end\n'.repeat(subgraphMatches.length - endMatches.length);
  }

  return clean;
};

export const MermaidDiagram: React.FC<MermaidDiagramProps> = ({ code, theme = 'default' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  
  // 全屏模态弹窗与交互缩放平移状态
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  useEffect(() => {
    let isMounted = true;
    setError(null);

    try {
      const mermaidTheme = theme === 'dark' ? 'dark' : (theme === 'vintage' ? 'neutral' : (theme === 'emerald' ? 'forest' : 'default'));
      mermaid.initialize({
        startOnLoad: false,
        suppressErrorRendering: true,
        theme: mermaidTheme as any,
        securityLevel: 'loose',
        fontFamily: 'inherit',
        themeVariables: {
          fontSize: '13px',
          primaryColor: '#3b82f6',
          primaryTextColor: theme === 'dark' ? '#f3f4f6' : '#1f2937',
          primaryBorderColor: '#2563eb',
          lineColor: '#6b7280',
          secondaryColor: '#10b981',
          tertiaryColor: '#f3f4f6',
          nodePadding: '14px'
        },
        flowchart: {
          htmlLabels: true,
          padding: 18,
          curve: 'basis'
        }
      });

      if (typeof (mermaid as any).setParseErrorHandler === 'function') {
        (mermaid as any).setParseErrorHandler(() => {});
      }

      const formattedCode = cleanAndFormatMermaidCode(code);
      // 每次渲染使用全新的全局唯一 ID，杜绝与历史 DOM 元素碰撞
      const renderId = `mmd_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      
      mermaid.render(renderId, formattedCode).then(({ svg: renderedSvg }) => {
        if (isMounted) {
          setSvg(renderedSvg);
          setError(null);
        }
      }).catch((err) => {
        if (typeof document !== 'undefined') {
          document.querySelectorAll('body > svg[id*="error"], body > [id*="error"], .error-icon, .error-text').forEach(el => el.remove());
        }
        if (isMounted) {
          console.warn('Mermaid render error:', err);
          setError('图表渲染语法异常');
        }
      });
    } catch (err: any) {
      if (typeof document !== 'undefined') {
        document.querySelectorAll('body > svg[id*="error"], body > [id*="error"], .error-icon, .error-text').forEach(el => el.remove());
      }
      if (isMounted) {
        setError(err.message || 'Mermaid 初始化失败');
      }
    }

    return () => {
      isMounted = false;
    };
  }, [code, theme]);

  // 全屏模式下监听 ESC 键关闭
  useEffect(() => {
    if (!isFullscreen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsFullscreen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreen]);

  const handleCopy = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    const formattedCode = cleanAndFormatMermaidCode(code);
    navigator.clipboard.writeText(formattedCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleDownloadSvg = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!svg) return;
    const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `architecture_diagram_${Date.now()}.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const openFullscreen = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
    setIsFullscreen(true);
  };

  // 画布鼠标拖拽平移与滚轮缩放逻辑
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    dragStartRef.current = {
      x: e.clientX - panOffset.x,
      y: e.clientY - panOffset.y
    };
  };

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging) return;
    setPanOffset({
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y
    });
  }, [isDragging]);

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.15 : -0.15;
    setZoomLevel(prev => Math.min(3.5, Math.max(0.3, +(prev + delta).toFixed(2))));
  };

  if (error) {
    return (
      <div className="my-5 p-4 rounded-xl theme-nested border border-dashed border-subtle text-xs space-y-2">
        <div className="flex items-center justify-between opacity-70">
          <span className="flex items-center gap-1.5 font-mono text-amber-500">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Mermaid Code</span>
          </span>
          <button
            type="button"
            onClick={handleCopy}
            className="opacity-70 hover:opacity-100 flex items-center gap-1 font-sans cursor-pointer"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? '已复制' : '复制代码'}</span>
          </button>
        </div>
        <pre className="overflow-x-auto font-mono text-[11px] p-2 bg-black/5 dark:bg-white/5 rounded-lg leading-relaxed">
          {cleanAndFormatMermaidCode(code)}
        </pre>
      </div>
    );
  }

  return (
    <>
      <div className="my-6 rounded-2xl theme-surface border border-subtle shadow-md overflow-hidden group">
        {/* 顶部工具条 */}
        <div className="px-4 py-2 bg-black/5 dark:bg-white/5 border-b border-subtle flex items-center justify-between text-xs opacity-75">
          <span className="font-mono text-[11px] font-semibold tracking-wider uppercase opacity-70 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            <span>架构图 / 演进路线图</span>
          </span>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={handleDownloadSvg}
              title="下载矢量图 (SVG)"
              className="p-1.5 rounded-md hover:bg-black/10 dark:hover:bg-white/10 transition cursor-pointer flex items-center gap-1 text-[11px]"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">导出 SVG</span>
            </button>
            <button
              type="button"
              onClick={openFullscreen}
              title="弹窗全屏放大查看"
              className="p-1.5 rounded-md hover:bg-black/10 dark:hover:bg-white/10 transition cursor-pointer flex items-center gap-1 text-[11px]"
            >
              <Maximize2 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">全屏放大</span>
            </button>
            <button
              type="button"
              onClick={handleCopy}
              title="复制 Mermaid 源码"
              className="p-1.5 rounded-md hover:bg-black/10 dark:hover:bg-white/10 transition cursor-pointer flex items-center gap-1 text-[11px]"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              <span className="hidden sm:inline">{copied ? '已复制' : '复制图表'}</span>
            </button>
          </div>
        </div>

        {/* SVG 内嵌展示容器（支持点击直接全屏查看） */}
        <div
          ref={containerRef}
          onClick={openFullscreen}
          title="点击弹窗全屏放大查看此图表"
          className="p-5 overflow-x-auto flex items-center justify-center min-h-[140px] [&_svg]:max-w-full [&_svg]:h-auto cursor-zoom-in relative group/canvas transition hover:bg-black/[0.01] dark:hover:bg-white/[0.01]"
        >
          <div className="w-full flex items-center justify-center [&_svg]:max-w-full [&_svg]:h-auto [&_svg]:mx-auto" dangerouslySetInnerHTML={{ __html: svg }} />
          <div className="absolute bottom-2.5 right-3.5 opacity-0 group-hover/canvas:opacity-100 transition duration-200 pointer-events-none">
            <span className="text-[10px] theme-nested px-2 py-1 rounded-lg font-sans opacity-90 border border-subtle shadow-md flex items-center gap-1">
              <Maximize2 className="w-3 h-3 text-blue-500" />
              <span>点击全屏交互放大</span>
            </span>
          </div>
        </div>
      </div>

      {/* 独立 Portal 全屏放大与缩放弹窗 Modal（脱离文章 DOM，杜绝被局部裁切或覆盖正文） */}
      {isFullscreen && typeof document !== 'undefined' && createPortal(
        <div 
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-6 select-none animate-in fade-in duration-200"
        >
          {/* 半透明背景遮罩 */}
          <div 
            className="absolute inset-0 bg-black/70 backdrop-blur-sm transition-opacity" 
            onClick={() => setIsFullscreen(false)} 
          />

          {/* 弹窗主体窗口 */}
          <div className="relative z-10 w-full h-full max-w-6xl theme-surface rounded-2xl flex flex-col overflow-hidden border border-subtle shadow-2xl animate-in zoom-in-95 duration-200">
            {/* 弹窗顶部控制栏 */}
            <div className="px-5 py-3.5 border-b border-subtle flex items-center justify-between bg-black/5 dark:bg-white/5">
              <div className="flex items-center gap-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" />
                <span className="text-sm font-bold tracking-tight">全屏交互架构图</span>
                <span className="text-[11px] opacity-60 font-mono hidden sm:inline">
                  按住鼠标左键可拖拽平移 · 滚轮缩放 · 按 ESC 退出
                </span>
              </div>

              <div className="flex items-center gap-2 sm:gap-3">
                {/* 缩放控制器 */}
                <div className="flex items-center gap-1 theme-nested px-2 py-1 rounded-xl text-xs shadow-inner">
                  <button
                    type="button"
                    onClick={() => setZoomLevel(prev => Math.max(0.3, +(prev - 0.2).toFixed(2)))}
                    title="缩小 (Zoom Out)"
                    className="p-1 rounded hover:bg-black/10 dark:hover:bg-white/10 cursor-pointer transition"
                  >
                    <ZoomOut className="w-3.5 h-3.5" />
                  </button>
                  <span className="font-mono px-1.5 min-w-[46px] text-center font-semibold text-[11px]">
                    {Math.round(zoomLevel * 100)}%
                  </span>
                  <button
                    type="button"
                    onClick={() => setZoomLevel(prev => Math.min(3.5, +(prev + 0.2).toFixed(2)))}
                    title="放大 (Zoom In)"
                    className="p-1 rounded hover:bg-black/10 dark:hover:bg-white/10 cursor-pointer transition"
                  >
                    <ZoomIn className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setZoomLevel(1);
                      setPanOffset({ x: 0, y: 0 });
                    }}
                    title="重置缩放与位置 (Reset)"
                    className="p-1 rounded hover:bg-black/10 dark:hover:bg-white/10 cursor-pointer ml-1 transition"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* 导出 SVG */}
                <button
                  type="button"
                  onClick={handleDownloadSvg}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl theme-card text-xs font-medium cursor-pointer shadow-sm hover:border-blue-500/50 transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">导出 SVG</span>
                </button>

                {/* 关闭按钮 */}
                <button
                  type="button"
                  onClick={() => setIsFullscreen(false)}
                  title="关闭全屏 (ESC)"
                  className="p-1.5 rounded-xl theme-nested opacity-70 hover:opacity-100 hover:text-red-500 cursor-pointer transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* 弹窗核心画布区 (支持自由拖拽平移与滚轮缩放) */}
            <div
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={handleWheel}
              className={`flex-1 overflow-hidden p-6 flex items-center justify-center bg-black/[0.03] dark:bg-white/[0.02] relative ${
                isDragging ? 'cursor-grabbing' : 'cursor-grab'
              }`}
            >
              <div
                style={{
                  transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
                  transformOrigin: 'center center',
                  transition: isDragging ? 'none' : 'transform 0.12s ease-out'
                }}
                className="[&_svg]:max-w-none [&_svg]:h-auto select-none pointer-events-auto"
                dangerouslySetInnerHTML={{ __html: svg }}
              />

              {/* 底部平移辅助提示 */}
              <div className="absolute bottom-3 left-1/2 -translate-x-1/2 opacity-40 pointer-events-none flex items-center gap-1 text-[11px] font-sans">
                <Move className="w-3 h-3" />
                <span>拖拽平移画布</span>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
};
