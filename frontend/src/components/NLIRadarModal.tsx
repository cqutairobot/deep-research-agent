import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Sparkles, 
  X, 
  CheckCircle2, 
  AlertTriangle, 
  HelpCircle, 
  RotateCw,
  Search,
  FileCheck2
} from 'lucide-react';
import { evaluateNLIRadar, NLIRadarData } from '../lib/api';

interface NLIRadarModalProps {
  taskId: string;
  title: string;
  report: string;
  citations?: any[];
  isOpen: boolean;
  onClose: () => void;
}

export const NLIRadarModal: React.FC<NLIRadarModalProps> = ({
  taskId,
  title,
  report,
  citations = [],
  isOpen,
  onClose
}) => {
  const [data, setData] = useState<NLIRadarData | null>(null);
  const [loading, setLoading] = useState(false);

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

      const res = await evaluateNLIRadar(taskId, report, citations, customLLMCfg);
      setData(res);
    } catch (e) {
      console.error('计算 NLI 事实雷达失败:', e);
    } finally {
      setLoading(false);
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
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-600 via-teal-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-100">
                  文献 NLI 语义蕴含裁判与抗幻觉雷达
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-emerald-400" />
                  NLI Grounding
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
              <div className="w-16 h-16 rounded-3xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center shadow-xl shadow-emerald-500/10 animate-pulse">
                <RotateCw className="w-8 h-8 text-emerald-400 animate-spin" />
              </div>
              <div className="space-y-1">
                <div className="text-sm font-bold text-slate-100">NLI 语义裁判正在逐句裁决...</div>
                <p className="text-xs text-slate-400 max-w-sm">
                  抽取全篇核心量化陈述句，与检索召回的学术切片进行 Entailment 语义蕴含对比。
                </p>
              </div>
            </div>
          ) : !data ? (
            <div className="text-center py-16 space-y-4">
              <p className="text-sm text-slate-400">未能成功生成 NLI 事实雷达</p>
              <button
                onClick={handleFetch}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow cursor-pointer"
              >
                重试评估
              </button>
            </div>
          ) : (
            <>
              {/* 核心双指标总览看板 */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-2xl bg-emerald-950/20 border border-emerald-500/30 space-y-1">
                  <div className="text-xs text-emerald-300 font-semibold flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    事实依据指数 (Grounding Score)
                  </div>
                  <div className="text-2xl font-extrabold text-emerald-400 font-mono">
                    {data.fact_grounding_score.toFixed(1)}
                    <span className="text-sm text-emerald-500 font-normal ml-1">/ 100</span>
                  </div>
                  <p className="text-[10px] text-slate-400">基于多源证据链交叉印证强度</p>
                </div>

                <div className="p-4 rounded-2xl bg-cyan-950/20 border border-cyan-500/30 space-y-1">
                  <div className="text-xs text-cyan-300 font-semibold flex items-center gap-1.5">
                    <FileCheck2 className="w-3.5 h-3.5" />
                    严格蕴含比例 (Entailment Rate)
                  </div>
                  <div className="text-2xl font-extrabold text-cyan-400 font-mono">
                    {data.entailment_rate.toFixed(1)}%
                  </div>
                  <p className="text-[10px] text-slate-400">论断直接源自文献原文比例</p>
                </div>
              </div>

              {/* 总结评语 */}
              <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-700/60 text-xs text-slate-300 leading-relaxed">
                <span className="font-bold text-slate-200">综合裁判评述：</span>
                {data.summary}
              </div>

              {/* 逐句核验清单 */}
              <div className="space-y-3">
                <div className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                  <Search className="w-4 h-4 text-emerald-400" />
                  关键论据 NLI 细粒度断言明细 ({data.evaluations.length} 处关键抽样)
                </div>

                <div className="space-y-2.5">
                  {data.evaluations.map((item, idx) => {
                    const isEntailment = item.verdict.toLowerCase().includes('entail');
                    const isNeutral = item.verdict.toLowerCase().includes('neutral');
                    return (
                      <div 
                        key={idx} 
                        className={`p-3.5 rounded-xl border text-xs space-y-1.5 ${
                          isEntailment 
                            ? 'bg-slate-900/60 border-emerald-500/30' 
                            : isNeutral
                            ? 'bg-slate-900/60 border-cyan-500/30'
                            : 'bg-slate-900/60 border-amber-500/30'
                        }`}
                      >
                        <div className="flex items-center justify-between font-bold">
                          <span className="text-slate-100 text-xs flex items-center gap-1.5">
                            {isEntailment ? (
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            ) : isNeutral ? (
                              <HelpCircle className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                            ) : (
                              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                            )}
                            <span className="truncate max-w-[340px]">{item.claim}</span>
                          </span>

                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-mono text-slate-400">
                              置信度 {(item.confidence * 100).toFixed(0)}%
                            </span>
                            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                              isEntailment 
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' 
                                : isNeutral 
                                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                                : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            }`}>
                              {item.verdict}
                            </span>
                          </div>
                        </div>

                        <p className="text-[11px] text-slate-400 pl-5 leading-relaxed">
                          <span className="text-slate-500">依据判定：</span>
                          {item.rationale}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>

        {/* 底部说明 */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/90 flex items-center justify-between text-xs text-slate-400">
          <span>基于自然语言推理 (NLI) 严格交叉验证</span>
          <button
            onClick={handleFetch}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span>重新执行 NLI 裁决</span>
          </button>
        </div>
      </div>
    </div>
  );
};
