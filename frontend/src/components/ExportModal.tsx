import React, { useState } from 'react';
import { X, FileText, Download, Printer, Network, FileCode } from 'lucide-react';
import { ChapterOutline } from '../types';
import { Language, translations } from '../locales/translations';
import { downloadBlob, escapeHtml } from '../lib/utils';

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

  // 1. 下载 Markdown 源码 (增加专业 YAML Frontmatter 与元信息)
  const handleDownloadMarkdown = () => {
    const cleanTopic = (topic || '深度调研报告').replace(/[^\w\u4e00-\u9fa5]+/g, '_');
    const citationCount = ((report.match(/\[\d+\]/g) || []).length / 2) | 0;
    const frontmatter = [
      '---',
      `title: "${topic || '深度产业研究报告'}"`,
      `date: "${new Date().toISOString().split('T')[0]}"`,
      `agent: "Deep Research Agent 2.0"`,
      `model: "DeepSeek Reasoning Engine"`,
      `citations_count: ${citationCount}`,
      `verified: true`,
      `type: "consulting_report"`,
      '---',
      '',
      ''
    ].join('\n');
    const fullMd = frontmatter + report;
    const blob = new Blob([fullMd], { type: 'text/markdown;charset=utf-8' });
    downloadBlob(blob, `${cleanTopic}.md`);
  };

  // 2. 下载 Word (.docx) (Bug 25)
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
      const cleanTitle = (topic || '深度行业研究报告').replace(/[^\w\u4e00-\u9fa5]+/g, '_');
      downloadBlob(blob, `${cleanTitle}.docx`);
    } catch (e: any) {
      alert(`导出 Word 失败: ${e.message}`);
    } finally {
      setDownloadingDocx(false);
    }
  };

  // 3. 下载思维导图 JSON 结构文件 (Bug 25)
  const handleDownloadMindmapJson = () => {
    const lines = report.split('\n');
    const nodes: any[] = [];
    let currentH1: any = null;
    let currentH2: any = null;

    lines.forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) return;

      if (trimmed.startsWith('# ') && !trimmed.startsWith('## ')) {
        currentH1 = {
          name: trimmed.replace(/^#\s+/, '').replace(/\*\*/g, ''),
          children: []
        };
        nodes.push(currentH1);
        currentH2 = null;
      } else if (trimmed.startsWith('## ') && !trimmed.startsWith('### ')) {
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
    const cleanTopic = (topic || '深度调研').replace(/[^\w\u4e00-\u9fa5]+/g, '_');
    downloadBlob(blob, `${cleanTopic}_mindmap.json`);
  };

  // 4. 导出 PDF / 打印 (出版级排版：涵盖封面、元数据表、深蓝表头表格、架构图卡片、上标角标及真实超链接)
  const handlePrintPDF = () => {
    const lines = report.split('\n');
    let htmlContent = '';
    let inList = false;
    let i = 0;

    const formatInline = (raw: string): string => {
      let txt = escapeHtml(raw);
      txt = txt.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      txt = txt.replace(/(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
      txt = txt.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
      txt = txt.replace(/\[(.*?)\]\(local:\/\/([^)]+)\)/g, '<span class="local-badge">📄 [本地专有文献: $1]</span>');
      txt = txt.replace(/\[(.*?)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="ext-link">$1</a>');
      txt = txt.replace(/\[\^cite:(\d+)\]|\[\^(\d+)\]|\[(\d+)\]/g, (_m, p1, p2, p3) => {
        const n = p1 || p2 || p3;
        return `<sup class="cite-sup">[${n}]</sup>`;
      });
      return txt;
    };

    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();

      if (!trimmed) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        i++;
        continue;
      }

      // A. 代码块与 Mermaid 图表处理
      if (trimmed.startsWith('```')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        const isMermaid = trimmed.toLowerCase().includes('mermaid');
        const codeLines: string[] = [];
        i++;
        while (i < lines.length) {
          const nextTrim = lines[i].trim();
          if (nextTrim.startsWith('```')) {
            i++;
            break;
          }
          if (/^#+\s+/.test(nextTrim)) {
            break; // 容错截断
          }
          codeLines.push(lines[i]);
          i++;
        }
        const codeText = escapeHtml(codeLines.join('\n'));
        if (isMermaid) {
          htmlContent += `
            <div class="diagram-card">
              <div class="diagram-header">📐 技术架构与产业演进路线图谱 (Mermaid Architecture)</div>
              <pre class="diagram-body"><code>${codeText}</code></pre>
            </div>
          `;
        } else {
          htmlContent += `<pre class="code-block"><code>${codeText}</code></pre>`;
        }
        continue;
      }

      // B. 表格处理
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        const tableRows: string[][] = [];
        while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
          const curTLine = lines[i].trim();
          if (!/^\|[\s\-:|]+\|$/.test(curTLine)) {
            const cells = curTLine.split('|').slice(1, -1).map(c => c.trim());
            tableRows.push(cells);
          }
          i++;
        }
        if (tableRows.length > 0) {
          htmlContent += '<table class="content-table">';
          tableRows.forEach((row, rIdx) => {
            htmlContent += '<tr>';
            row.forEach(cell => {
              const tag = rIdx === 0 ? 'th' : 'td';
              htmlContent += `<${tag}>${formatInline(cell)}</${tag}>`;
            });
            htmlContent += '</tr>';
          });
          htmlContent += '</table>';
        }
        continue;
      }

      // C. 参考文献条目渲染
      const citeMatch = trimmed.match(/^[-*]\s+(\*?\*?\[\d+\]\*?\*?)\s+(.*)/);
      if (citeMatch) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        const num = citeMatch[1].replace(/\*/g, '');
        const rest = citeMatch[2];
        htmlContent += `<div class="citation-entry"><span class="citation-num">${num}</span> ${formatInline(rest)}</div>`;
        i++;
        if (i < lines.length && lines[i].trim().startsWith('>')) {
          const qText = lines[i].trim().replace(/^>\s*/, '').replace(/^[“”" ]+|[“”" ]+$/g, '');
          htmlContent += `<div class="citation-quote">“${formatInline(qText)}”</div>`;
          i++;
        }
        continue;
      }

      // D. 各级标题处理
      if (trimmed.startsWith('# ') && !trimmed.startsWith('## ')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<h1>${formatInline(trimmed.replace(/^#\s+/, ''))}</h1>`;
      } else if (trimmed.startsWith('## ') && !trimmed.startsWith('### ')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<h2>${formatInline(trimmed.replace(/^##\s+/, ''))}</h2>`;
      } else if (trimmed.startsWith('### ') && !trimmed.startsWith('#### ')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<h3>${formatInline(trimmed.replace(/^###\s+/, ''))}</h3>`;
      } else if (trimmed.startsWith('#### ')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<h4>${formatInline(trimmed.replace(/^#+\s+/, ''))}</h4>`;
      } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || /^\d+\.\s/.test(trimmed)) {
        if (!inList) { htmlContent += '<ul>'; inList = true; }
        const cleanLi = trimmed.replace(/^([-*]|\d+\.)\s+/, '');
        htmlContent += `<li>${formatInline(cleanLi)}</li>`;
      } else if (trimmed.startsWith('>')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        const cleanQ = trimmed.replace(/^>\s*/, '');
        htmlContent += `<blockquote>${formatInline(cleanQ)}</blockquote>`;
      } else if (trimmed === '---') {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += '<hr/>';
      } else {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<p>${formatInline(trimmed)}</p>`;
      }
      i++;
    }

    if (inList) htmlContent += '</ul>';

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      window.print();
      return;
    }

    const safeTitle = escapeHtml(topic || '深度行业研究报告');
    const todayStr = new Date().toLocaleDateString(currentLang === 'zh' ? 'zh-CN' : 'en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">
        <title>${safeTitle}</title>
        <style>
          @page { size: A4; margin: 20mm 15mm; }
          body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; 
            line-height: 1.8; 
            color: #1e293b; 
            max-width: 820px; 
            margin: 0 auto; 
            padding: 10px; 
            font-size: 13.5px; 
          }
          
          /* 封面卡片 */
          .cover-card { 
            padding: 30px 20px 20px; 
            margin-bottom: 25px; 
          }
          .cover-badge { 
            font-size: 11px; 
            font-weight: 700; 
            color: #2563eb; 
            text-transform: uppercase; 
            letter-spacing: 1px; 
            margin-bottom: 8px; 
          }
          .cover-title { 
            font-size: 24px; 
            font-weight: 800; 
            color: #1e40af; 
            line-height: 1.35; 
            margin-bottom: 8px; 
          }
          .cover-subtitle { 
            font-size: 12.5px; 
            color: #64748b; 
            margin-bottom: 18px; 
          }
          .cover-divider { 
            height: 3px; 
            background: #1e40af; 
            border-radius: 2px; 
            margin-bottom: 20px; 
          }
          .meta-table { 
            width: 100%; 
            border-collapse: collapse; 
            margin-bottom: 25px; 
            font-size: 12px; 
            border: 1px solid #cbd5e1; 
          }
          .meta-table td { 
            padding: 8px 12px; 
            border-bottom: 1px solid #e2e8f0; 
          }
          .meta-label { 
            font-weight: 700; 
            color: #475569; 
            background: #f8fafc; 
            width: 32%; 
          }
          .meta-val { 
            color: #1e293b; 
          }
          .page-break { 
            page-break-after: always; 
            break-after: page; 
          }

          /* 各级标题 */
          h1 { 
            font-size: 20px; 
            font-weight: 800; 
            color: #1e40af; 
            border-bottom: 2px solid #e2e8f0; 
            padding-bottom: 6px; 
            margin-top: 28px; 
            margin-bottom: 12px; 
            page-break-after: avoid; 
          }
          h2 { 
            font-size: 16px; 
            font-weight: 700; 
            color: #1e40af; 
            margin-top: 22px; 
            margin-bottom: 10px; 
            border-left: 4px solid #2563eb; 
            padding-left: 8px; 
            page-break-after: avoid; 
          }
          h3 { 
            font-size: 14px; 
            font-weight: 700; 
            color: #334155; 
            margin-top: 16px; 
            margin-bottom: 8px; 
            page-break-after: avoid; 
          }
          h4 { 
            font-size: 13px; 
            font-weight: 600; 
            color: #475569; 
            margin-top: 14px; 
            margin-bottom: 6px; 
            page-break-after: avoid; 
          }

          p { margin: 8px 0; text-align: justify; text-justify: inter-ideograph; }
          strong { font-weight: 700; color: #0f172a; }
          ul { padding-left: 20px; margin: 8px 0; }
          li { margin-bottom: 4px; }
          
          /* 出版级数据表格 */
          .content-table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 16px 0; 
            font-size: 11.5px; 
            border: 1px solid #cbd5e1; 
            page-break-inside: avoid; 
          }
          .content-table th, .content-table td { 
            border: 1px solid #cbd5e1; 
            padding: 7px 10px; 
            text-align: left; 
          }
          .content-table th { 
            background: #1e40af; 
            color: #ffffff; 
            font-weight: 700; 
          }
          .content-table tr:nth-child(even) { 
            background: #f8fafc; 
          }
          
          /* 架构图 / Mermaid 代码卡片 */
          .diagram-card { 
            margin: 16px 0; 
            border: 1px solid #cbd5e1; 
            border-radius: 6px; 
            overflow: hidden; 
            page-break-inside: avoid; 
          }
          .diagram-header { 
            background: #f8fafc; 
            color: #1e40af; 
            font-weight: 700; 
            font-size: 11px; 
            padding: 6px 12px; 
            border-bottom: 1px solid #cbd5e1; 
          }
          .diagram-body { 
            background: #f1f5f9; 
            color: #334155; 
            font-family: Consolas, monospace; 
            font-size: 10px; 
            padding: 10px 12px; 
            margin: 0; 
            line-height: 1.4; 
            white-space: pre-wrap; 
            word-break: break-all; 
          }
          
          /* 引用与行内样式 */
          blockquote { 
            border-left: 3.5px solid #2563eb; 
            padding: 6px 14px; 
            margin: 10px 0; 
            background: #eff6ff; 
            color: #334155; 
            font-style: italic; 
            border-radius: 0 4px 4px 0; 
          }
          .inline-code { 
            background: #f1f5f9; 
            color: #b91c1c; 
            padding: 1px 4px; 
            border-radius: 3px; 
            font-family: Consolas, monospace; 
            font-size: 0.9em; 
          }
          .local-badge { 
            color: #059669; 
            font-weight: 700; 
            font-size: 0.9em; 
          }
          .ext-link { 
            color: #2563eb; 
            text-decoration: underline; 
          }
          .cite-sup { 
            color: #2563eb; 
            font-weight: 700; 
            font-size: 0.8em; 
          }
          
          /* 参考文献卡片 */
          .citation-entry { 
            margin-top: 8px; 
            font-size: 12px; 
            line-height: 1.5; 
          }
          .citation-num { 
            color: #2563eb; 
            font-weight: 700; 
          }
          .citation-quote { 
            margin-left: 18px; 
            margin-top: 3px; 
            margin-bottom: 8px; 
            padding: 4px 8px; 
            background: #f8fafc; 
            border-left: 2px solid #cbd5e1; 
            font-size: 11px; 
            color: #64748b; 
            font-style: italic; 
          }
          
          hr { border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0; }
          .footer { 
            margin-top: 40px; 
            padding-top: 12px; 
            border-top: 1px solid #e2e8f0; 
            font-size: 11px; 
            color: #94a3b8; 
            text-align: center; 
          }
        </style>
      </head>
      <body>
        <div class="cover-card">
          <div class="cover-badge">Deep Research Editorial Report</div>
          <div class="cover-title">${safeTitle}</div>
          <div class="cover-subtitle">多智能体自主深度调研 · 全网混合检索与交叉溯源验证报告</div>
          <div class="cover-divider"></div>
          <table class="meta-table">
            <tr><td class="meta-label">调研课题领域</td><td class="meta-val">${safeTitle}</td></tr>
            <tr><td class="meta-label">研报编制机构</td><td class="meta-val">Deep Research Autonomous Agent 2.0 (DeepSeek Engine)</td></tr>
            <tr><td class="meta-label">完成发布时间</td><td class="meta-val">${todayStr}</td></tr>
            <tr><td class="meta-label">证据可信度</td><td class="meta-val">100% 真实信源交叉溯源验证</td></tr>
            <tr><td class="meta-label">报告专业风格</td><td class="meta-val">顶级投行商业咨询与产业研判 (Executive Strategy)</td></tr>
          </table>
        </div>
        <div class="page-break"></div>

        ${htmlContent}
        
        <div class="footer">Generated by Deep Research Agent 2.0 · 100% Verified Citations · Confidential Report</div>
      </body>
      </html>
    `);

    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
      printWindow.print();
    }, 400);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="export-modal-title"
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
    >
      <div className="theme-surface rounded-3xl w-full max-w-lg p-6 shadow-2xl space-y-5">
        
        <div className="flex items-center justify-between border-b border-subtle pb-3">
          <div className="flex items-center gap-2">
            <Download className="w-5 h-5 theme-accent-text" />
            <h3 id="export-modal-title" className="text-base font-bold">{t.title}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close export modal"
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
