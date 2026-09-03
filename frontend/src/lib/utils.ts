/**
 * 前端通用安全工具库 (Bug 18, 21, 23, 25)
 */

export interface CitationDomainInfo {
  label: string;
  isLocal: boolean;
  isHttp: boolean;
}

/**
 * 安全提取引证来源域名或本地文件名，防止 new URL() 抛错崩溃 (Bug 18)
 */
export function formatCitationDomain(url: string | undefined): CitationDomainInfo {
  if (!url) {
    return { label: '未指定来源', isLocal: false, isHttp: false };
  }

  if (url.startsWith('local://')) {
    const filename = url.replace('local://', '');
    return {
      label: `本地私有文件: ${filename}`,
      isLocal: true,
      isHttp: false
    };
  }

  try {
    const parsed = new URL(url);
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
      return {
        label: parsed.hostname.replace(/^www\./, ''),
        isLocal: false,
        isHttp: true
      };
    }
  } catch (e) {
    // URL 解析异常兜底
  }

  return {
    label: url.length > 25 ? url.slice(0, 22) + '...' : url,
    isLocal: false,
    isHttp: false
  };
}

/**
 * 统一下载 Blob 文件并在安全延时后清理 ObjectURL (Bug 25)
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // 延迟 1 秒释放，确保各浏览器（含 Safari）完成下载启动
  setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 1000);
}

/**
 * 统一标题 Slug 生成器，支持中英文与去重 ID (Bug 21)
 */
export function slugifyHeading(text: string, index?: number): string {
  if (!text) return `section-${index !== undefined ? index : 0}`;
  const clean = text
    .replace(/\[\^cite:\d+\]/g, '')
    .replace(/\[\d+\]/g, '')
    .replace(/\*\*/g, '')
    .replace(/`/g, '')
    .trim()
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fa5]+/g, '-');

  const base = clean.replace(/^-+|-+$/g, '') || `section-${index !== undefined ? index : 0}`;
  return index !== undefined ? `${base}-${index}` : base;
}

/**
 * 安全 HTML 实体转义，彻底杜绝 XSS 注入 (Bug 23)
 */
export function escapeHtml(str: string): string {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * 识别某一行是否属于 Mermaid 图表语法内容
 */
export function isMermaidStatement(line: string): boolean {
  const t = line.trim();
  return (
    t.startsWith('graph ') ||
    t.startsWith('flowchart ') ||
    t.startsWith('subgraph') ||
    t.startsWith('sequenceDiagram') ||
    t.startsWith('gantt') ||
    t.startsWith('classDiagram') ||
    t.startsWith('stateDiagram') ||
    t.startsWith('pie') ||
    t.startsWith('erDiagram') ||
    t.startsWith('journey') ||
    t.startsWith('mindmap') ||
    t.startsWith('quadrantChart') ||
    t.startsWith('gitGraph') ||
    t.startsWith('participant ') ||
    t.startsWith('actor ') ||
    t.startsWith('autonumber') ||
    t.startsWith('dateFormat ') ||
    t.startsWith('section ') ||
    t.includes('-->') ||
    t.includes('---') ||
    t.includes('==>') ||
    t.includes('-.->') ||
    t.includes('->>') ||
    t.includes('-->>') ||
    t === 'end' ||
    /^[A-Za-z0-9_\u4e00-\u9fa5]+\s*\[.+\]$/.test(t) ||
    /^[A-Za-z0-9_\u4e00-\u9fa5]+\s*(-->|==>|-\.->|->>|-->>)/.test(t) ||
    /^\s*%%/.test(line)
  );
}

/**
 * 智能 Markdown 块级切分器：
 * 1. 保护代码块 ``` 围栏内的空行不被肢解，保持架构图完整性；
 * 2. 遇到章节标题 # / ## 等自动闭合未闭合的代码块或公式块；
 * 3. 严格区分单行 LaTeX 公式 ($$...$$) 与多行公式块，避免状态被卡死在 inMathBlock 中；
 * 4. 遇到代码块、公式块、标题或图表前，强制将前序累积的普通文本段落 flush 输出；
 * 5. 自动合并无围栏裸 Mermaid 的多行与子图；
 */
export function splitMarkdownBlocks(content: string): string[] {
  if (!content) return [];
  const lines = content.split('\n');
  const blocks: string[] = [];
  let currentBlock: string[] = [];
  let inCodeBlock = false;
  let inMathBlock = false;
  let inBareMermaid = false;

  const flushBlock = () => {
    if (currentBlock.length > 0) {
      const joined = currentBlock.join('\n').trim();
      if (joined) {
        blocks.push(joined);
      }
      currentBlock = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // 1. 容错：如果代码块内遇到了 Markdown 标题，说明大模型漏写了 ``` 闭合标签，强制闭合！
    if (inCodeBlock && /^#{1,6}\s/.test(trimmed)) {
      inCodeBlock = false;
      currentBlock.push('```');
      flushBlock();
    }

    // 2. 容错：如果数学公式块内遇到了 Markdown 标题或代码块，强制闭合
    if (inMathBlock && (/^#{1,6}\s/.test(trimmed) || trimmed.startsWith('```'))) {
      inMathBlock = false;
      flushBlock();
    }

    // 3. 处理代码块 ``` 
    if (trimmed.startsWith('```')) {
      // 如果是单行闭合的代码块: ```code```
      if (trimmed.length > 3 && trimmed.slice(3).includes('```')) {
        flushBlock();
        blocks.push(trimmed);
        continue;
      }

      if (!inCodeBlock) {
        // 开启新代码块前，先将之前的段落/文本 flush
        flushBlock();
        inCodeBlock = true;
        currentBlock.push(line);
      } else {
        // 闭合代码块
        inCodeBlock = false;
        currentBlock.push(line);
        flushBlock();
      }
      continue;
    }

    // 如果在代码块内部，原样保留
    if (inCodeBlock) {
      currentBlock.push(line);
      continue;
    }

    // 4. 处理 LaTeX 块级公式 ($$ 或 \[)
    // 4.1 单行完整独立公式: $$...$$ 或 \[...\] (允许末尾带逗号/句号标点)
    const isSingleLineMath = 
      (trimmed.startsWith('$$') && trimmed.length > 2 && /\$\$\s*[,.]?$/.test(trimmed)) ||
      (trimmed.startsWith('\\[') && trimmed.length > 2 && /\\\]\s*[,.]?$/.test(trimmed));

    if (isSingleLineMath) {
      flushBlock();
      blocks.push(trimmed);
      continue;
    }

    // 4.2 多行公式开启/闭合 ($$)
    if (trimmed.startsWith('$$') || trimmed === '\\[' || trimmed === '\\]') {
      if (!inMathBlock) {
        flushBlock();
        inMathBlock = true;
        currentBlock.push(line);
      } else {
        inMathBlock = false;
        currentBlock.push(line);
        flushBlock();
      }
      continue;
    }

    if (inMathBlock) {
      currentBlock.push(line);
      continue;
    }

    // 5. 处理标题 (#, ##, ###, ####, #####, ######)
    if (/^#{1,6}\s/.test(trimmed)) {
      flushBlock();
      blocks.push(trimmed);
      continue;
    }

    // 6. 处理裸 Mermaid (无 ``` 围栏的独立图表)
    if (!inBareMermaid && (
      trimmed.startsWith('graph ') ||
      trimmed.startsWith('flowchart ') ||
      trimmed.startsWith('subgraph ') ||
      trimmed.startsWith('sequenceDiagram') ||
      trimmed.startsWith('gantt')
    )) {
      flushBlock();
      inBareMermaid = true;
    }

    if (inBareMermaid) {
      if (trimmed === '') {
        let nextIsMermaid = false;
        for (let j = i + 1; j < Math.min(lines.length, i + 6); j++) {
          const nextTrim = lines[j].trim();
          if (nextTrim !== '') {
            nextIsMermaid = isMermaidStatement(nextTrim);
            break;
          }
        }
        if (nextIsMermaid) {
          currentBlock.push(line);
          continue;
        } else {
          inBareMermaid = false;
          flushBlock();
          continue;
        }
      } else if (!isMermaidStatement(trimmed)) {
        inBareMermaid = false;
        flushBlock();
      }
    }

    // 7. 空行切分普通段落
    if (trimmed === '') {
      flushBlock();
      continue;
    }

    currentBlock.push(line);
  }

  flushBlock();
  return blocks;
}

/**
 * 跨浏览器、跨协议（含非安全上下文如 http://0.0.0.0:8000、内网 IP 与 HTTP 协议）的万能剪贴板复制工具
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (!text) return false;

  // 1. 若支持 Clipboard API 且处于 Secure Context（localhost, https），优先使用现代异步 API
  if (typeof navigator !== 'undefined' && navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (e) {
      console.warn('navigator.clipboard.writeText failed, falling back to textarea execCommand:', e);
    }
  }

  // 2. 降级方案：创建隐藏 textarea 执行 document.execCommand('copy')
  try {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    textArea.setAttribute('readonly', '');
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);

    textArea.focus();
    textArea.select();
    textArea.setSelectionRange(0, 999999);

    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);
    if (successful) return true;
  } catch (err) {
    console.error('execCommand fallback failed:', err);
  }

  return false;
}

