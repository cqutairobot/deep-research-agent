import React, { useState, useEffect } from 'react';
import { 
  MessageSquareQuote, 
  Sparkles, 
  X, 
  Copy, 
  Check, 
  TrendingUp, 
  Compass, 
  Share2,
  Twitter,
  Flame,
  RotateCw
} from 'lucide-react';
import { generateSocialQuotes, SocialQuotesData } from '../lib/api';
import { copyToClipboard } from '../lib/utils';

interface SocialQuotesModalProps {
  taskId: string;
  title: string;
  report: string;
  isOpen: boolean;
  onClose: () => void;
}

export const SocialQuotesModal: React.FC<SocialQuotesModalProps> = ({
  taskId,
  title,
  report,
  isOpen,
  onClose
}) => {
  const [data, setData] = useState<SocialQuotesData | null>(null);
  const [loading, setLoading] = useState(false);
  const [copiedPlatform, setCopiedPlatform] = useState<string | null>(null);
  const [activePlatform, setActivePlatform] = useState<'twitter_thread' | 'jike_post' | 'xiaohongshu'>('twitter_thread');

  useEffect(() => {
    if (!isOpen) return;
    if (data) return;
    handleFetch();
  }, [isOpen, taskId]);

  const handleFetch = async () => {
    setLoading(true);
    try {
      let customLLMCfg = null;
      try {
        const saved = localStorage.getItem('deep_research_custom_llm');
        if (saved) customLLMCfg = JSON.parse(saved);
      } catch {}

      const res = await generateSocialQuotes(taskId, title, report, customLLMCfg);
      setData(res);
    } catch (e) {
      console.error('提炼社交金句失败:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async (text: string, platformKey: string) => {
    const success = await copyToClipboard(text);
    if (success) {
      setCopiedPlatform(platformKey);
      setTimeout(() => setCopiedPlatform(null), 2000);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh] text-white"
        onClick={e => e.stopPropagation()}
      >
        {/* 顶栏 */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-amber-500 via-rose-500 to-pink-600 flex items-center justify-center shadow-lg shadow-rose-500/20">
              <MessageSquareQuote className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-100">
                  社交媒体爆款金句与跨平台文案
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-rose-400" />
                  Social Highlights
                </span>
              </div>
              <p className="text-xs text-slate-400 truncate max-w-md mt-0.5">{title}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 主体区 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 space-y-4 text-center animate-in fade-in">
              <div className="w-16 h-16 rounded-3xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center shadow-xl shadow-rose-500/10 animate-pulse">
                <RotateCw className="w-8 h-8 text-rose-400 animate-spin" />
              </div>
              <div className="space-y-1">
                <div className="text-sm font-bold text-slate-100">AI 正在提炼最具穿透力的社交金句...</div>
                <p className="text-xs text-slate-400 max-w-sm">
                  从近万字长文中凝练颠覆性认知、三大量化预判，并自动适配 𝕏、即刻与小红书排版。
                </p>
              </div>
            </div>
          ) : !data ? (
            <div className="text-center py-16 space-y-4">
              <p className="text-sm text-slate-400">未能成功生成社交金句</p>
              <button
                onClick={handleFetch}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold shadow cursor-pointer"
              >
                重试生成
              </button>
            </div>
          ) : (
            <>
              {/* 颠覆性认知金句卡片 */}
              <div className="p-5 rounded-2xl bg-gradient-to-br from-rose-950/40 via-purple-950/20 to-slate-900 border border-rose-500/40 shadow-xl relative overflow-hidden space-y-2">
                <div className="text-[11px] font-bold text-rose-400 flex items-center gap-1.5 uppercase tracking-wider">
                  <Flame className="w-3.5 h-3.5" />
                  颠覆性认知金句 (Core Punchline)
                </div>
                <p className="text-base font-bold text-slate-100 leading-relaxed font-serif italic">
                  “{data.punchline}”
                </p>
              </div>

              {/* 三大产业预判 */}
              <div className="space-y-2.5">
                <div className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-cyan-400" />
                  三大核心量化预判与拐点 (Predictions)
                </div>
                <div className="grid grid-cols-1 gap-2.5">
                  {data.predictions.map((pred, i) => (
                    <div key={i} className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/60 flex items-start gap-3 text-xs leading-relaxed text-slate-200">
                      <span className="text-[11px] font-mono font-bold px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 shrink-0 mt-0.5">
                        0{i + 1}
                      </span>
                      <span>{pred}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 关键行动策略 */}
              {data.action_advice && (
                <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/30 flex items-start gap-3 text-xs text-amber-200/90 leading-relaxed">
                  <Compass className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold text-amber-300">行动战略启示：</span>
                    {data.action_advice}
                  </div>
                </div>
              )}

              {/* 跨平台发布文案抽屉 */}
              <div className="space-y-3 pt-2 border-t border-slate-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setActivePlatform('twitter_thread')}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                        activePlatform === 'twitter_thread'
                          ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <Twitter className="w-3.5 h-3.5" />
                      <span>𝕏 / Twitter 串</span>
                    </button>

                    <button
                      onClick={() => setActivePlatform('jike_post')}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                        activePlatform === 'jike_post'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <span>🟡 即刻 / 朋友圈</span>
                    </button>

                    <button
                      onClick={() => setActivePlatform('xiaohongshu')}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                        activePlatform === 'xiaohongshu'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <span>📕 小红书笔记</span>
                    </button>
                  </div>

                  <button
                    onClick={() => handleCopy(data.platforms[activePlatform], activePlatform)}
                    className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white text-xs font-bold shadow-md transition cursor-pointer flex items-center gap-1.5"
                  >
                    {copiedPlatform === activePlatform ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-white" />
                        <span>已复制全篇文案</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>一键复制发布文案</span>
                      </>
                    )}
                  </button>
                </div>

                {/* 文案预览框 */}
                <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed max-h-52 overflow-y-auto select-all">
                  {data.platforms[activePlatform]}
                </div>
              </div>
            </>
          )}
        </div>

        {/* 底部动作栏 */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/90 flex items-center justify-between text-xs text-slate-400">
          <span>大语言模型自动优化社交裂变文案排版</span>
          <button
            onClick={handleFetch}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5 text-rose-400" />
            <span>重新提炼金句</span>
          </button>
        </div>
      </div>
    </div>
  );
};
