import React, { useState, useRef, useEffect } from 'react';
import { X, Send, MessageSquare, Bot, User, Sparkles, Anchor, ShieldAlert, BarChart3, TrendingUp, FileText, Copy, Check } from 'lucide-react';
import { CitationSource } from '../types';
import { Language, translations } from '../locales/translations';

interface FollowUpDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  report: string;
  citations: CitationSource[];
  initialQuestion?: string;
  onAnchorClick?: (anchorText: string) => void;
  currentLang?: Language;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

function parseChatInlineMarkdown(text: string, onAnchorClick?: (anchor: string) => void): React.ReactNode[] {
  if (!text) return [];
  const regex = /(\*\*.*?\*\*|`.*?`|\[⚓\s*[^\]]+\])/g;
  const parts = text.split(regex);

  return parts.map((part, idx) => {
    if (!part) return null;
    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return <strong key={idx} className="font-bold text-inherit">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return <code key={idx} className="theme-nested px-1 rounded font-mono text-[11px]">{part.slice(1, -1)}</code>;
    }
    if (part.startsWith('[⚓') && part.endsWith(']')) {
      const label = part.slice(1, -1).trim();
      return (
        <button
          key={idx}
          type="button"
          onClick={() => onAnchorClick && onAnchorClick(label)}
          className="inline-flex items-center gap-1 px-2 py-0.5 mx-0.5 rounded-md bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 text-[10px] font-semibold hover:bg-amber-500/25 transition cursor-pointer"
          title="点击在正文中定位并高亮此段落"
        >
          <Anchor className="w-2.5 h-2.5" />
          <span>{label.replace(/^⚓\s*/, '')}</span>
        </button>
      );
    }
    return <span key={idx}>{part}</span>;
  });
}

function renderChatMarkdown(content: string, onAnchorClick?: (anchor: string) => void) {
  const blocks = content.split('\n\n');
  return blocks.map((block, bIdx) => {
    const trimmed = block.trim();
    if (!trimmed) return null;

    if (trimmed.startsWith('# ')) {
      return (
        <h3 key={bIdx} className="text-sm font-bold border-b border-subtle pb-1 mb-2 mt-2">
          {parseChatInlineMarkdown(trimmed.replace(/^#\s+/, ''), onAnchorClick)}
        </h3>
      );
    }
    if (trimmed.startsWith('## ') || trimmed.startsWith('### ')) {
      return (
        <h4 key={bIdx} className="text-xs font-bold theme-accent-text mb-1.5 mt-2">
          {parseChatInlineMarkdown(trimmed.replace(/^#{2,3}\s+/, ''), onAnchorClick)}
        </h4>
      );
    }
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || /^\d+\.\s/.test(trimmed)) {
      const items = trimmed.split('\n');
      return (
        <ul key={bIdx} className="space-y-1 pl-3 border-l-2 border-subtle my-1.5">
          {items.map((it, iIdx) => (
            <li key={iIdx} className="text-xs leading-relaxed">
              {parseChatInlineMarkdown(it.replace(/^([-*]|\d+\.)\s+/, ''), onAnchorClick)}
            </li>
          ))}
        </ul>
      );
    }

    return (
      <p key={bIdx} className="text-xs leading-relaxed my-1.5">
        {parseChatInlineMarkdown(trimmed, onAnchorClick)}
      </p>
    );
  });
}

export const FollowUpDrawer: React.FC<FollowUpDrawerProps> = ({
  isOpen,
  onClose,
  report,
  citations,
  initialQuestion,
  onAnchorClick,
  currentLang = 'zh'
}) => {
  const t = translations[currentLang].chat;
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: t.welcome
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleCopyMsg = (idx: number, text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx(null), 2000);
    });
  };

  useEffect(() => {
    setMessages(prev => {
      if (prev.length === 1 && prev[0].role === 'assistant') {
        return [{ role: 'assistant', content: t.welcome }];
      }
      return prev;
    });
  }, [currentLang, t.welcome]);

  useEffect(() => {
    if (initialQuestion) {
      setInput(initialQuestion);
    }
  }, [initialQuestion]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!isOpen) return null;

  const handleSend = async (customQuestion?: string) => {
    const userMsg = (customQuestion || input).trim();
    if (!userMsg || loading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const resp = await fetch('/api/v1/research/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userMsg,
          report_context: report
        })
      });

      if (resp.ok) {
        const data = await resp.json();
        setMessages(prev => [...prev, { role: 'assistant', content: data.answer || '未能获取解答内容。' }]);
      } else {
        const err = await resp.json().catch(() => ({ detail: '网络请求失败' }));
        setMessages(prev => [...prev, { role: 'assistant', content: `【服务响应错误】${err.detail || '大模型暂时无法响应'}` }]);
      }
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `【网络异常】无法连接到大模型后端服务 (${e.message})` }]);
    } finally {
      setLoading(false);
    }
  };

  // 快捷追问动作卡片
  const quickTemplates = [
    {
      icon: <FileText className="w-3 h-3 text-blue-500" />,
      title: currentLang === 'zh' ? '📑 提炼为高管 1 页汇报' : '📑 1-Page Exec Summary',
      prompt: currentLang === 'zh' ? '请将上述整份研报核心提炼为适合企业高管汇报的 1 页纸精要，包含 3 大核心发现与 3 条决策建议。' : 'Please summarize this report into a 1-page executive briefing with 3 key findings and 3 recommendations.'
    },
    {
      icon: <ShieldAlert className="w-3 h-3 text-red-500" />,
      title: currentLang === 'zh' ? '⚠️ 评估核心风险与劣势' : '⚠️ Risk & Downside Assessment',
      prompt: currentLang === 'zh' ? '请深入评估研报中提到的商业化瓶颈与主要方案的潜在劣势，列出前 3 大不可忽视的核心风险。' : 'Please evaluate the key commercialization risks and downsides highlighted in the report.'
    },
    {
      icon: <BarChart3 className="w-3 h-3 text-purple-500" />,
      title: currentLang === 'zh' ? '📊 提取关键数据对比表' : '📊 Extract Metric Matrix',
      prompt: currentLang === 'zh' ? '请将研报中所有出现的具体量化指标（能量密度、循环寿命、量产时间、成本等）整理为一个完整的 Markdown 对比汇总表。' : 'Please extract all quantitative metrics and dates into a comprehensive comparison table.'
    }
  ];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="followup-drawer-title"
      className="fixed inset-y-0 right-0 z-50 w-full sm:w-[500px] theme-surface border-l border-subtle shadow-2xl flex flex-col animate-in slide-in-from-right duration-300"
    >
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-subtle">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg theme-badge flex items-center justify-center">
            <MessageSquare className="w-4 h-4 theme-accent-text" />
          </div>
          <div>
            <h3 id="followup-drawer-title" className="text-sm font-bold">{t.title}</h3>
            <p className="text-[11px] opacity-70">{t.subtitle}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close follow-up drawer"
          className="opacity-70 hover:opacity-100 p-1.5 rounded-lg theme-nested transition cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* 消息历史 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex gap-3 text-xs leading-relaxed ${
              m.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {m.role === 'assistant' && (
              <div className="w-6 h-6 rounded-md theme-btn-primary text-white flex items-center justify-center shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5" />
              </div>
            )}
            <div
              className={`p-3.5 rounded-2xl max-w-[85%] leading-relaxed ${
                m.role === 'user'
                  ? 'theme-btn-primary text-white rounded-br-none shadow-md'
                  : 'theme-nested rounded-bl-none shadow-sm'
              }`}
            >
              {m.role === 'assistant' ? (
                <div>
                  {renderChatMarkdown(m.content, onAnchorClick)}
                  <div className="flex justify-end mt-1.5 pt-1 border-t border-subtle/30">
                    <button
                      type="button"
                      onClick={() => handleCopyMsg(idx, m.content)}
                      className="text-[10px] opacity-60 hover:opacity-100 flex items-center gap-1 transition cursor-pointer"
                    >
                      {copiedIdx === idx ? <Check className="w-2.5 h-2.5 text-emerald-500" /> : <Copy className="w-2.5 h-2.5" />}
                      <span>{copiedIdx === idx ? (currentLang === 'zh' ? '已复制' : 'Copied') : (currentLang === 'zh' ? '复制回答' : 'Copy')}</span>
                    </button>
                  </div>
                </div>
              ) : (
                m.content
              )}
            </div>
            {m.role === 'user' && (
              <div className="w-6 h-6 rounded-md theme-nested flex items-center justify-center shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-2 text-xs opacity-70 items-center pl-8">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
            <span>{t.thinking}</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 快捷追问模板卡片 */}
      <div className="px-4 py-2 border-t border-subtle flex gap-2 overflow-x-auto text-[11px]">
        {quickTemplates.map((tpl, i) => (
          <button
            key={i}
            type="button"
            onClick={() => handleSend(tpl.prompt)}
            className="theme-card px-2.5 py-1.5 rounded-xl shrink-0 opacity-85 hover:opacity-100 transition cursor-pointer flex items-center gap-1.5 border border-subtle shadow-xs"
          >
            {tpl.icon}
            <span>{tpl.title}</span>
          </button>
        ))}
      </div>

      {/* 输入框 */}
      <div className="p-4 border-t border-subtle theme-nested">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={t.inputPlaceholder}
            className="flex-1 theme-input rounded-xl px-3.5 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/30 transition"
          />
          <button
            type="button"
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="p-2 theme-btn-primary rounded-xl disabled:opacity-50 transition cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

    </div>
  );
};
