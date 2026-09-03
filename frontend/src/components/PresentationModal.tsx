import React, { useState, useEffect } from 'react';
import { 
  Presentation, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  ExternalLink, 
  X, 
  Loader2,
  Layers,
  LayoutGrid,
  FileCheck
} from 'lucide-react';
import { preparePresentation, getLivePresentationUrl, PreparePresentationResult } from '../lib/api';
import { LOCAL_STORAGE_KEY } from './ModelSettingsModal';

interface PresentationModalProps {
  isOpen: boolean;
  onClose: () => void;
  taskId: string;
  reportTitle: string;
}

export const PresentationModal: React.FC<PresentationModalProps> = ({
  isOpen,
  onClose,
  taskId,
  reportTitle
}) => {
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(10);
  const [currentStep, setCurrentStep] = useState(1);
  const [result, setResult] = useState<PreparePresentationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !taskId) return;

    setLoading(true);
    setProgress(12);
    setCurrentStep(1);
    setError(null);
    setResult(null);

    // 动态平滑推进进度条与步骤动画
    const progressTimer = setInterval(() => {
      setProgress(prev => {
        if (prev < 30) {
          setCurrentStep(1);
          return prev + 6;
        } else if (prev < 65) {
          setCurrentStep(2);
          return prev + 4;
        } else if (prev < 88) {
          setCurrentStep(3);
          return prev + 2;
        }
        return prev;
      });
    }, 400);

    // 读取前端用户自定义模型配置
    let customLLMCfg: any = null;
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (saved) {
        customLLMCfg = JSON.parse(saved);
      }
    } catch (e) {
      console.warn('读取自定义模型配置失败', e);
    }

    // 发起服务端智能编排
    preparePresentation(taskId, customLLMCfg, false)
      .then(res => {
        clearInterval(progressTimer);
        setProgress(100);
        setCurrentStep(4);
        setResult(res);
        setLoading(false);

        // 编排完成后延时 700ms 自动打开演示文稿大屏
        setTimeout(() => {
          const presentationUrl = getLivePresentationUrl(taskId);
          window.open(presentationUrl, '_blank');
        }, 700);
      })
      .catch(err => {
        clearInterval(progressTimer);
        setLoading(false);
        setError(err.message || '演示文稿编排失败，请重试');
      });

    return () => {
      clearInterval(progressTimer);
    };
  }, [isOpen, taskId]);

  if (!isOpen) return null;

  const handleManualOpen = () => {
    if (taskId) {
      window.open(getLivePresentationUrl(taskId), '_blank');
      onClose();
    }
  };

  const steps = [
    {
      id: 1,
      title: '深度解析研报脉络与核心论点',
      desc: '解构宏观产业链图谱、各章节逻辑与量化事实',
      icon: Layers
    },
    {
      id: 2,
      title: 'LLM 演讲总监提炼 2x2 信息矩阵',
      desc: '自适应展开子节，生成高密度咨询级论点卡片',
      icon: Sparkles
    },
    {
      id: 3,
      title: '编排 16:9 出版级全景大屏视觉',
      desc: '计算视口比例边界，装配决策启示与快捷交互',
      icon: LayoutGrid
    },
    {
      id: 4,
      title: '演示文稿编排就绪，开启放映',
      desc: '准备就绪，支持键盘翻页、全屏模式与侧边点击',
      icon: FileCheck
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-lg bg-slate-900/95 border border-slate-700/60 rounded-2xl shadow-2xl overflow-hidden p-6 sm:p-8 text-white"
        onClick={e => e.stopPropagation()}
      >
        {/* 关闭按钮 */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          title="关闭"
        >
          <X className="w-5 h-5" />
        </button>

        {/* 头部图标与标题 */}
        <div className="flex items-center gap-3.5 mb-5">
          <div className="relative flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 shadow-lg shadow-blue-500/25">
            <Presentation className="w-6 h-6 text-white animate-pulse" />
            {loading && (
              <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-cyan-500"></span>
              </span>
            )}
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              {loading ? 'AI 演示文稿智能编排中' : error ? '编排遇到问题' : '演示文稿编排完成'}
            </h3>
            <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">
              {reportTitle || '深度研究汇报演示'}
            </p>
          </div>
        </div>

        {/* 动态进度条 */}
        <div className="mb-6">
          <div className="flex justify-between items-center text-xs text-slate-400 mb-1.5 font-mono">
            <span>{loading ? '自适应深度提炼中 (无固定页数限制)' : result ? `已生成 ${result.slide_count} 页大屏` : '状态'}</span>
            <span className="font-semibold text-cyan-400">{progress}%</span>
          </div>
          <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-700/50">
            <div 
              className={`h-full rounded-full transition-all duration-300 ${
                error 
                  ? 'bg-rose-500' 
                  : 'bg-gradient-to-r from-blue-500 via-cyan-400 to-emerald-400'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* 编排步骤列表 */}
        <div className="space-y-3 mb-6">
          {steps.map((s) => {
            const isFinished = progress === 100 || currentStep > s.id;
            const isCurrent = loading && currentStep === s.id;
            const Icon = s.icon;

            return (
              <div 
                key={s.id}
                className={`flex items-start gap-3 p-2.5 rounded-xl transition border ${
                  isCurrent 
                    ? 'bg-blue-500/10 border-blue-500/30 text-blue-300' 
                    : isFinished 
                    ? 'bg-slate-800/40 border-slate-700/40 text-slate-300' 
                    : 'opacity-40 border-transparent text-slate-500'
                }`}
              >
                <div className="mt-0.5">
                  {isFinished ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 text-cyan-400 animate-spin shrink-0" />
                  ) : (
                    <Icon className="w-4 h-4 text-slate-500 shrink-0" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold flex items-center justify-between">
                    <span>{s.title}</span>
                    {isCurrent && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300">
                        处理中...
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5 leading-tight">
                    {s.desc}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="p-3 mb-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
            <div className="flex-1">{error}</div>
          </div>
        )}

        {/* 底部操作区 */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-800">
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>基于实际篇幅自适应展开，无页数限制</span>
          </div>

          <div className="flex items-center gap-2">
            {loading ? (
              <div className="flex items-center gap-2 text-xs text-cyan-400 font-medium px-3 py-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>提炼中...</span>
              </div>
            ) : result ? (
              <button
                type="button"
                onClick={handleManualOpen}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white text-xs font-semibold shadow-lg shadow-cyan-500/25 flex items-center gap-1.5 transition cursor-pointer"
              >
                <span>立即进入全屏放映</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                type="button"
                onClick={onClose}
                className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition cursor-pointer"
              >
                关闭
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
