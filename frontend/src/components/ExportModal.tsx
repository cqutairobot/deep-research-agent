import React, { useState } from 'react';
import { X, FileText, Download, Printer, Network, FileCode } from 'lucide-react';
import { ChapterOutline } from '../types';
import { Language, translations } from '../locales/translations';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: string;
  topic: string;
  outline?: ChapterOutline[];
  currentLang?: Language;
}

export const ExportModal: React.FC<ExportModalProps> = ({
  isOpen,
  onClose,
  report,
  topic,
  outline,
  currentLang = 'zh'
}) => {
  const t = translations[currentLang].export;
  const [downloadingDocx, setDownloadingDocx] = useState(false);

  if (!isOpen) return null;

  // 1. 下载 Markdown 源码
  const handleDownloadMarkdown = () => {
    const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const cleanTopic = (topic || '深度调研报告').replace(/[^\w\u4e00-\u9fa5]+/g, '_');
    link.download = `${cleanTopic}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // 2. 下载 Word (.docx)
  const handleDownloadDocx = async () => {
    setDownloadingDocx(true);
    try {
      const resp = await fetch('/api/v1/research/export/docx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report: report,
          title: topic || '深度行业研究报告'
        })
      });

      if (!resp.ok) {
        throw new Error('导出 Word 失败');
      }

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${(topic || '深度行业研究报告').replace(/[^\w\u4e00-\u9fa5]+/g, '_')}.docx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(`导出 Word 失败: ${e.message}`);
    } finally {
      setDownloadingDocx(false);
    }
  };

  // 3. 下载思维导图 JSON 结构文件
  const handleDownloadMindmapJson = () => {
    const lines = report.split('\n');
    const nodes: any[] = [];
    let currentH1: any = null;
    let currentH2: any = null;

    lines.forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) return;

      if (trimmed.startsWith('# ')) {
        currentH1 = {
          name: trimmed.replace(/^#\s+/, '').replace(/\*\*/g, ''),
          children: []
        };
        nodes.push(currentH1);
        currentH2 = null;
      } else if (trimmed.startsWith('## ')) {
        currentH2 = {
          name: trimmed.replace(/^##\s+/, '').replace(/\*\*/g, ''),
          children: []
        };
        if (currentH1) currentH1.children.push(currentH2);
        else nodes.push(currentH2);
      } else if (trimmed.startsWith('### ') || trimmed.startsWith('- ') || /^\d+\.\s/.test(trimmed)) {
        const leaf = {
          name: trimmed.replace(/^(###\s+|[-*]\s+|\d+\.\s+)/, '').replace(/\*\*/g, '')
        };
        if (leaf.name.length > 2 && leaf.name.length < 80) {
          if (currentH2) currentH2.children.push(leaf);
          else if (currentH1) currentH1.children.push(leaf);
        }
      }
    });

    const mindmapData = {
      root: {
        name: topic || '深度研究课题全景',
        children: nodes
      }
    };

    const blob = new Blob([JSON.stringify(mindmapData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${(topic || '深度调研').replace(/[^\w\u4e00-\u9fa5]+/g, '_')}_mindmap.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // 4. 导出 PDF / 打印
  const handlePrintPDF = () => {
    const lines = report.split('\n');
    let htmlContent = '';
    let inList = false;

    lines.forEach(line => {
      const trimmed = line.trim();
      if (!trimmed) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        return;
      }

      if (trimmed.startsWith('# ') && !trimmed.startsWith('## ')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<h1>${trimmed.replace(/^#\s+/, '')}</h1>`;
      } else if (trimmed.startsWith('## ') && !trimmed.startsWith('### ')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<h2>${trimmed.replace(/^##\s+/, '')}</h2>`;
      } else if (trimmed.startsWith('### ') && !trimmed.startsWith('#### ')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<h3>${trimmed.replace(/^###\s+/, '')}</h3>`;
      } else if (trimmed.startsWith('#### ')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<h4>${trimmed.replace(/^####\s+/, '')}</h4>`;
      } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        if (!inList) { htmlContent += '<ul>'; inList = true; }
        htmlContent += `<li>${trimmed.replace(/^[-*]\s+/, '')}</li>`;
      } else {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        let pText = trimmed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        htmlContent += `<p>${pText}</p>`;
      }
    });

    if (inList) htmlContent += '</ul>';

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      window.print();
      return;
    }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>${topic || '深度研究报告'}</title>
        <style>
          @page { size: A4; margin: 20mm; }
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; line-height: 1.8; color: #1f2937; max-width: 800px; margin: 0 auto; padding: 20px; font-size: 14px; }
          h1 { font-size: 24px; font-weight: bold; border-bottom: 2px solid #2563eb; padding-bottom: 8px; margin-top: 24px; color: #111827; }
          h2 { font-size: 18px; font-weight: bold; color: #1e40af; margin-top: 20px; border-left: 4px solid #2563eb; padding-left: 8px; }
          h3 { font-size: 15px; font-weight: bold; color: #374151; margin-top: 16px; }
          h4 { font-size: 14px; font-weight: bold; color: #4b5563; margin-top: 14px; }
          p { margin: 10px 0; text-align: justify; }
          strong { font-weight: bold; color: #111827; }
          ul { padding-left: 20px; margin: 10px 0; }
          li { margin-bottom: 4px; }
          table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 12px; }
          th, td { border: 1px solid #d1d5db; padding: 8px 12px; text-align: left; }
          th { background: #f3f4f6; font-weight: bold; }
          blockquote { border-left: 3px solid #93c5fd; padding: 8px 12px; margin: 12px 0; background: #eff6ff; color: #4b5563; font-style: italic; }
          .footer { margin-top: 40px; padding-top: 12px; border-top: 1px solid #e5e7eb; font-size: 11px; color: #9ca3af; text-align: center; }
        </style>
      </head>
      <body>
        ${htmlContent}
        <div class="footer">Generated by Deep Research Agent 2.0 · 100% Verified Citations</div>
      </body>
      </html>
    `);

    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
      printWindow.print();
    }, 300);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="theme-surface rounded-3xl w-full max-w-lg p-6 shadow-2xl space-y-5">
        
        <div className="flex items-center justify-between border-b border-subtle pb-3">
          <div className="flex items-center gap-2">
            <Download className="w-5 h-5 theme-accent-text" />
            <h3 className="text-base font-bold">{t.title}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="opacity-70 hover:opacity-100 p-1 rounded-lg theme-nested transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-2.5">
          {/* 1. Word (.docx) 导出 */}
          <button
            type="button"
            onClick={handleDownloadDocx}
            disabled={downloadingDocx}
            className="w-full theme-card p-3.5 rounded-xl flex items-center justify-between text-left transition group cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-blue-600/10 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-semibold group-hover:theme-accent-text transition">
                  {downloadingDocx ? t.docxGenerating : t.docxTitle}
                </div>
                <div className="text-[11px] opacity-70">{t.docxDesc}</div>
              </div>
            </div>
            <Download className="w-4 h-4 opacity-50 group-hover:opacity-100 transition" />
          </button>

          {/* 2. Markdown 源码 */}
          <button
            type="button"
            onClick={handleDownloadMarkdown}
            className="w-full theme-card p-3.5 rounded-xl flex items-center justify-between text-left transition group cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                <FileCode className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-semibold group-hover:theme-accent-text transition">
                  {t.mdTitle}
                </div>
                <div className="text-[11px] opacity-70">{t.mdDesc}</div>
              </div>
            </div>
            <Download className="w-4 h-4 opacity-50 group-hover:opacity-100 transition" />
          </button>

          {/* 3. PDF / 打印 */}
          <button
            type="button"
            onClick={handlePrintPDF}
            className="w-full theme-card p-3.5 rounded-xl flex items-center justify-between text-left transition group cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-indigo-500/10 text-indigo-500 flex items-center justify-center">
                <Printer className="w-4 h-4" />
              </div>
              <div>
                <div className="text-xs font-semibold group-hover:theme-accent-text transition">
                  {t.pdfTitle}
                </div>
                <div className="text-[11px] opacity-70">{t.pdfDesc}</div>
              </div>
            </div>
            <Printer className="w-4 h-4 opacity-50 group-hover:opacity-100 transition" />
          </button>

          {/* 4. 下载思维导图 JSON 结构 */}
          <button
            type="button"
            onClick={handleDownloadMindmapJson}
            className="w-full theme-card p-3.5 rounded-xl flex items-center justify-between text-left transition group cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-purple-500/10 text-purple-500 flex items-center justify-center">
                <Network className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-semibold group-hover:theme-accent-text transition">
                  {t.mindmapJsonTitle}
                </div>
                <div className="text-[11px] opacity-70">{t.mindmapJsonDesc}</div>
              </div>
            </div>
            <Download className="w-4 h-4 opacity-50 group-hover:opacity-100 transition" />
          </button>
        </div>

        <div className="pt-1 text-center">
          <button
            type="button"
            onClick={onClose}
            className="text-xs opacity-70 hover:opacity-100 cursor-pointer"
          >
            {t.close}
          </button>
        </div>

      </div>
    </div>
  );
};
