import React, { useState, useEffect } from 'react';
import { 
  GitFork, 
  Sparkles, 
  X, 
  Copy, 
  Check, 
  Layers, 
  Scale, 
  AlertCircle, 
  Target, 
  RotateCw,
  Maximize2
} from 'lucide-react';
import { generateCausalMindmap, CausalMindmapData } from '../lib/api';
import { MermaidDiagram } from './MermaidDiagram';
import { copyToClipboard } from '../lib/utils';

interface CausalMindmapModalProps {
  taskId: string;
  title: string;
  report: string;
  isOpen: boolean;
  onClose: () => void;
}

export const CausalMindmapModal: React.FC<CausalMindmapModalProps> = ({
  taskId,
  title,
  report,
  isOpen,
  onClose
}) => {
  const [data, setData] = useState<CausalMindmapData | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'diagram' | 'matrix'>('diagram');

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

      const res = await generateCausalMindmap(taskId, title, report, customLLMCfg);
      setData(res);
    } catch (e) {
      console.error('提炼因果脑图失败:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyMermaid = async () => {
    if (!data?.mermaid_code) return;
    const success = await copyToClipboard(data.mermaid_code);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-4xl bg-slate-900 border border-slate-700/80 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh] text-white"
        onClick={e => e.stopPropagation()}
      >
        {/* 顶栏 */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-cyan-600 via-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <GitFork className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-100">
                  因果机制与方案权衡知识图谱
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-cyan-400" />
                  Causal & Tradeoff
                </span>
              </div>
              <p className="text-xs text-slate-400 truncate max-w-lg mt-0.5">{title}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="p-1.5 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* 核心展示区 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-24 space-y-4 text-center animate-in fade-in">
              <div className="w-16 h-16 rounded-3xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center shadow-xl shadow-cyan-500/10 animate-pulse">
                <RotateCw className="w-8 h-8 text-cyan-400 animate-spin" />
              </div>
              <div className="space-y-1">
                <div className="text-sm font-bold text-slate-100">AI 正在深度解构因果矛盾链条...</div>
                <p className="text-xs text-slate-400 max-w-sm">
                  打破目录标题粗糙截取，提炼底层工程瓶颈、技术路线分水岭与 Trade-offs 权衡矩阵。
                </p>
              </div>
            </div>
          ) : !data ? (
            <div className="text-center py-20 space-y-4">
              <p className="text-sm text-slate-400">未能成功加载知识图谱</p>
              <button
                onClick={handleFetch}
                className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold shadow cursor-pointer"
              >
                重试提炼
              </button>
            </div>
          ) : (
            <>
              {/* 导图主纲要横幅 */}
              <div className="p-4 rounded-2xl bg-cyan-950/30 border border-cyan-500/30 flex items-start gap-3">
                <Scale className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="text-xs font-bold text-cyan-300">核心矛盾与因果推演脉络</div>
                  <p className="text-xs text-slate-300 leading-relaxed">{data.summary}</p>
                </div>
              </div>

              {/* 视图切换 */}
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setActiveTab('diagram')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                      activeTab === 'diagram'
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Layers className="w-3.5 h-3.5" />
                    <span>交互式因果拓扑图</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('matrix')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                      activeTab === 'matrix'
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Target className="w-3.5 h-3.5" />
                    <span>节点权衡详情清单 ({data.nodes.length})</span>
                  </button>
                </div>

                <button
                  onClick={handleCopyMermaid}
                  className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition cursor-pointer flex items-center gap-1.5"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? '已复制 Mermaid' : '复制图表源码'}</span>
                </button>
              </div>

              {/* 选项卡内容 */}
              {activeTab === 'diagram' ? (
                <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800/90 overflow-x-auto min-h-[380px] flex items-center justify-center">
                  <div className="w-full">
                    <MermaidDiagram code={data.mermaid_code} />
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {data.nodes.map((node, idx) => {
                    const isTradeoff = node.type === 'tradeoff';
                    const isChallenge = node.type === 'challenge';
                    const isSolution = node.type === 'solution';
                    return (
                      <div
                        key={idx}
                        className={`p-3.5 rounded-xl border text-xs space-y-1.5 ${
                          isTradeoff
                            ? 'bg-purple-950/20 border-purple-500/30'
                            : isChallenge
                            ? 'bg-rose-950/20 border-rose-500/30'
                            : isSolution
                            ? 'bg-emerald-950/20 border-emerald-500/30'
                            : 'bg-slate-900/60 border-slate-800'
                        }`}
                      >
                        <div className="flex items-center justify-between font-bold">
                          <span className="text-slate-100">{node.label}</span>
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                            isTradeoff 
                              ? 'bg-purple-500/20 text-purple-300' 
                              : isChallenge 
                              ? 'bg-rose-500/20 text-rose-300' 
                              : 'bg-cyan-500/20 text-cyan-300'
                          }`}>
                            {node.type}
                          </span>
                        </div>
                        {node.detail && (
                          <p className="text-slate-400 leading-relaxed">{node.detail}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>

        {/* 底部说明 */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/90 flex items-center justify-between text-xs text-slate-400">
          <span>基于 Mermaid 拓扑树动态计算因果传导</span>
          <button
            onClick={handleFetch}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>重新提炼因果图谱</span>
          </button>
        </div>
      </div>
    </div>
  );
};
