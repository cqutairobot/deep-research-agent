import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, MessageSquare, X, Loader2, BookOpen, Check } from 'lucide-react';
import { explainTerm, GlossaryResult } from '../lib/api';
import { LOCAL_STORAGE_KEY } from './ModelSettingsModal';
import { copyToClipboard } from '../lib/utils';

interface GlossaryPopoverProps {
  term: string;
  context: string;
  position: { x: number; y: number };
  onClose: () => void;
  onAskInQA?: (query: string) => void;
}

export const GlossaryPopover: React.FC<GlossaryPopoverProps> = ({
  term,
  context,
  position,
  onClose,
  onAskInQA
}) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<GlossaryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let customLLMCfg: any = null;
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (saved) customLLMCfg = JSON.parse(saved);
    } catch (e) {}

    setLoading(true);
    setError(null);

    explainTerm(term, context, customLLMCfg)
      .then(res => {
        setData(res);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message || '获取释义失败');
        setLoading(false);
      });
  }, [term, context]);

  // 计算视口防止溢出屏幕边界
  const screenW = typeof window !== 'undefined' ? window.innerWidth : 1200;
  const screenH = typeof window !== 'undefined' ? window.innerHeight : 800;
  const popoverW = 340;
  
  let posX = position.x - popoverW / 2;
  if (posX < 16) posX = 16;
  if (posX + popoverW > screenW - 16) posX = screenW - popoverW - 16;
  
  let posY = position.y + 12;
  // 若距离底部太近，向上翻转
  if (posY + 220 > screenH) {
    posY = Math.max(16, position.y - 210);
  }

  const handleCopy = async () => {
    if (data?.explanation) {
      const ok = await copyToClipboard(`【${term}】：${data.explanation}`);
      if (ok) {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }
    }
  };

  return (
    <div 
      ref={popoverRef}
      style={{ left: `${posX}px`, top: `${posY}px` }}
      className="fixed z-50 w-[340px] bg-slate-900/95 border border-cyan-500/40 rounded-2xl shadow-2xl backdrop-blur-xl p-4 text-slate-100 animate-in fade-in zoom-in-95 duration-150"
      onClick={e => e.stopPropagation()}
    >
      {/* 顶栏：术语标题与关闭 */}
      <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-slate-800">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-6 h-6 rounded-lg bg-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0">
            <BookOpen className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-bold text-cyan-300 truncate max-w-[190px]">
            {term}
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/60 shrink-0">
            秒级释义
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 内容区域 */}
      <div className="min-h-[70px]">
        {loading ? (
          <div className="space-y-2 py-2">
            <div className="h-3 bg-slate-800 rounded animate-pulse w-full"></div>
            <div className="h-3 bg-slate-800 rounded animate-pulse w-5/6"></div>
            <div className="h-3 bg-slate-800 rounded animate-pulse w-4/6"></div>
            <div className="flex items-center gap-1.5 text-[11px] text-cyan-400/80 pt-1">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>结合研报上下文提炼通俗定义中...</span>
            </div>
          </div>
        ) : error ? (
          <div className="text-xs text-rose-400 py-2 leading-relaxed">
            {error}
          </div>
        ) : (
          <div className="text-xs text-slate-200 leading-relaxed font-normal py-1 select-text">
            {data?.explanation}
          </div>
        )}
      </div>

      {/* 底部动作栏 */}
      {!loading && !error && (
        <div className="flex items-center justify-between pt-2.5 mt-2.5 border-t border-slate-800/80 text-[11px]">
          <button
            onClick={handleCopy}
            className="text-slate-400 hover:text-slate-200 flex items-center gap-1 transition cursor-pointer"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Sparkles className="w-3 h-3 text-amber-400" />}
            <span>{copied ? '已复制' : '复制释义'}</span>
          </button>

          {onAskInQA && (
            <button
              onClick={() => {
                onAskInQA(`请深入帮我分析「${term}」在本文中的工程落地挑战与最新突破`);
                onClose();
              }}
              className="px-2.5 py-1 rounded-lg bg-blue-600/30 hover:bg-blue-600/50 border border-blue-500/40 text-blue-300 flex items-center gap-1 transition cursor-pointer font-medium"
            >
              <MessageSquare className="w-3 h-3" />
              <span>在 Q&A 中追问</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};
