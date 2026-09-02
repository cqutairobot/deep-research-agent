import React, { useState, useRef, useEffect } from 'react';
import { X, Send, MessageSquare, Bot, User } from 'lucide-react';
import { CitationSource } from '../types';
import { Language, translations } from '../locales/translations';

interface FollowUpDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  report: string;
  citations: CitationSource[];
  initialQuestion?: string;
  currentLang?: Language;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

function parseChatInlineMarkdown(text: string): React.ReactNode[] {
  if (!text) return [];
  const regex = /(\*\*.*?\*\*|`.*?`)/g;
  const parts = text.split(regex);

  return parts.map((part, idx) => {
    if (!part) return null;
    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return <strong key={idx} className="font-bold text-inherit">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return <code key={idx} className="theme-nested px-1 rounded font-mono text-[11px]">{part.slice(1, -1)}</code>;
    }
    return <span key={idx}>{part}</span>;
  });
}

function renderChatMarkdown(content: string) {
  const blocks = content.split('\n\n');
  return blocks.map((block, bIdx) => {
    const trimmed = block.trim();
    if (!trimmed) return null;

    if (trimmed.startsWith('# ')) {
      return (
        <h3 key={bIdx} className="text-sm font-bold border-b border-subtle pb-1 mb-2 mt-2">
          {parseChatInlineMarkdown(trimmed.replace(/^#\s+/, ''))}
        </h3>
      );
    }
    if (trimmed.startsWith('## ') || trimmed.startsWith('### ')) {
      return (
        <h4 key={bIdx} className="text-xs font-bold theme-accent-text mb-1.5 mt-2">
          {parseChatInlineMarkdown(trimmed.replace(/^#{2,3}\s+/, ''))}
        </h4>
      );
    }
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || /^\d+\.\s/.test(trimmed)) {
      const items = trimmed.split('\n');
      return (
        <ul key={bIdx} className="space-y-1 pl-3 border-l-2 border-subtle my-1.5">
          {items.map((it, iIdx) => (
            <li key={iIdx} className="text-xs leading-relaxed">
              {parseChatInlineMarkdown(it.replace(/^([-*]|\d+\.)\s+/, ''))}
            </li>
          ))}
        </ul>
      );
    }

    return (
      <p key={bIdx} className="text-xs leading-relaxed my-1.5">
        {parseChatInlineMarkdown(trimmed)}
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
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[480px] theme-surface border-l border-subtle shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
      
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-subtle">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg theme-badge flex items-center justify-center">
            <MessageSquare className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold">{t.title}</h3>
            <p className="text-[11px] opacity-70">{t.subtitle}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
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
              {m.role === 'assistant' ? renderChatMarkdown(m.content) : m.content}
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

      {/* 快速追问建议气泡 */}
      <div className="px-4 py-2 border-t border-subtle flex gap-1.5 overflow-x-auto text-[11px]">
        <button
          type="button"
          onClick={() => handleSend(t.prompt1Text)}
          className="theme-card px-2.5 py-1 rounded-lg shrink-0 opacity-80 hover:opacity-100 transition cursor-pointer"
        >
          {t.quickPrompt1}
        </button>
        <button
          type="button"
          onClick={() => handleSend(t.prompt2Text)}
          className="theme-card px-2.5 py-1 rounded-lg shrink-0 opacity-80 hover:opacity-100 transition cursor-pointer"
        >
          {t.quickPrompt2}
        </button>
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
