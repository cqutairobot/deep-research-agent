import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { CommandHero } from './components/CommandHero';
import { OutlineCanvas } from './components/OutlineCanvas';
import { BentoRadarDashboard } from './components/BentoRadarDashboard';
import { ReportViewer } from './components/ReportViewer';
import { FollowUpDrawer } from './components/FollowUpDrawer';
import { HistoryDrawer } from './components/HistoryDrawer';
import { ExportModal } from './components/ExportModal';
import { MindmapModal } from './components/MindmapModal';
import { ModelSettingsModal, getStoredCustomLLMConfig } from './components/ModelSettingsModal';
import { ThemeType } from './components/ThemeSelector';
import { Language } from './locales/translations';
import { ChapterOutline, CitationSource, TaskStatus, ReportStyle, CustomLLMConfig } from './types';
import { createTask, approveOutline, cancelTask, subscribeToTaskStream } from './lib/api';

const VALID_THEMES: ThemeType[] = ['vintage', 'light', 'emerald', 'dark'];
const VALID_LANGS: Language[] = ['zh', 'en'];

export const App: React.FC = () => {
  // 主题配色状态 (持久化到 localStorage，带白名单运行时校验 Bug 27)
  const [theme, setTheme] = useState<ThemeType>(() => {
    const saved = localStorage.getItem('app-theme') as ThemeType;
    return VALID_THEMES.includes(saved) ? saved : 'vintage';
  });

  // 国际化语言状态 (持久化到 localStorage，带白名单运行时校验 Bug 27)
  const [lang, setLang] = useState<Language>(() => {
    const saved = localStorage.getItem('app-lang') as Language;
    return VALID_LANGS.includes(saved) ? saved : 'zh';
  });

  const [currentStep, setCurrentStep] = useState<number>(1);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus>('pending');
  const [query, setQuery] = useState<string>('');
  
  // 调研流状态
  const [outline, setOutline] = useState<ChapterOutline[]>([]);
  const [clarification, setClarification] = useState<string>('');
  const [citations, setCitations] = useState<CitationSource[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [criticFeedback, setCriticFeedback] = useState<string>('');
  const [iterationCount, setIterationCount] = useState<number>(1);
  const [maxIterations, setMaxIterations] = useState<number>(2);
  const [finalReport, setFinalReport] = useState<string>('');
  const [uploadedDocs, setUploadedDocs] = useState<any[]>([]);
  
  // 弹窗与抽屉
  const [isQAOpen, setIsQAOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isMindmapOpen, setIsMindmapOpen] = useState(false);
  const [isModelSettingsOpen, setIsModelSettingsOpen] = useState(false);
  const [customLLMConfig, setCustomLLMConfig] = useState<CustomLLMConfig | null>(getStoredCustomLLMConfig);
  const [deepDiveQuestion, setDeepDiveQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const unsubscribeRef = useRef<(() => void) | null>(null);

  // 同步切换主题
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('app-theme', theme);
  }, [theme]);

  // 同步切换语言
  useEffect(() => {
    localStorage.setItem('app-lang', lang);
  }, [lang]);

  useEffect(() => {
    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
      }
    };
  }, []);

  // 1. 发起调研任务 (支持本地文档混合 RAG 与自定义模型网关)
  const handleStartResearch = async (
    userQuery: string,
    depth: 'quick' | 'standard' | 'deep',
    style: ReportStyle,
    localDocs?: any[]
  ) => {
    // 若已有正在运行的任务，先行取消后台 (Bug 15)
    if (taskId && (currentStep === 2 || currentStep === 3)) {
      cancelTask(taskId).catch(() => {});
    }

    setIsLoading(true);
    setErrorMsg(null);
    setQuery(userQuery);
    setUploadedDocs(localDocs || []);
    setLogs([`[System] Initializing research task: "${userQuery}" (${localDocs?.length || 0} local documents)...`]);
    
    const maxIter = depth === 'quick' ? 1 : (depth === 'deep' ? 3 : 2);
    setMaxIterations(maxIter);

    try {
      const res = await createTask(
        userQuery, 
        depth, 
        style, 
        false, 
        maxIter, 
        localDocs, 
        customLLMConfig || undefined
      );
      const tid = res.task_id;
      setTaskId(tid);

      if (unsubscribeRef.current) unsubscribeRef.current();
      
      const unsub = subscribeToTaskStream(
        tid,
        (eventType, data) => {
          handleStreamEvent(eventType, data);
        },
        (err) => {
          console.error('SSE Error:', err);
          setErrorMsg(lang === 'zh' ? '实时流传输中断，请重试或刷新' : 'Stream connection error');
          setIsLoading(false);
        }
      );
      unsubscribeRef.current = unsub;

    } catch (err: any) {
      setErrorMsg(err.message || '发起调研失败，请检查网络或后端服务');
      setIsLoading(false);
    }
  };

  // 2. 处理实时流事件
  const handleStreamEvent = (eventType: string, data: any) => {
    switch (eventType) {
      case 'status':
        if (data.state?.outline && data.state.outline.length > 0) {
          setOutline(data.state.outline);
          if (data.state.clarification) setClarification(data.state.clarification);
          if (data.status === 'waiting_outline_approval' || data.status === 'planning') {
            setCurrentStep(2);
            setIsLoading(false);
          }
        }
        if (data.state?.citations) setCitations(data.state.citations);
        if (data.state?.logs) setLogs(data.state.logs);
        break;

      case 'thought':
        if (data.message) {
          setLogs(prev => [...prev, data.message]);
        }
        break;

      case 'outline_ready':
        if (data.outline) {
          setOutline(data.outline);
          if (data.clarification) setClarification(data.clarification);
          setCurrentStep(2);
          setIsLoading(false);
        }
        break;

      case 'waiting_approval':
        setCurrentStep(2);
        setIsLoading(false);
        break;

      case 'search':
        if (data.iteration) setIterationCount(data.iteration);
        if (data.message) setLogs(prev => [...prev, data.message]);
        break;

      case 'facts_extracted':
        if (data.citations) setCitations(data.citations);
        if (data.outline) setOutline(data.outline);
        break;

      case 'critic_evaluated':
        if (data.feedback) setCriticFeedback(data.feedback);
        if (data.iteration) setIterationCount(data.iteration);
        break;

      case 'completed':
        // 无论 final_report 是否为空，均正常结束加载态 (Bug 17)
        setFinalReport(data.final_report || '');
        if (data.citations) setCitations(data.citations);
        setCurrentStep(4);
        setIsLoading(false);
        break;

      case 'failed':
      case 'error':
        // 统一失败终态事件处理 (Bug 1)
        setErrorMsg(data.message || data.error || '任务执行发生异常');
        setIsLoading(false);
        break;

      case 'cancelled':
        setIsLoading(false);
        break;

      default:
        break;
    }
  };

  // 3. 人工确认大纲
  const handleApproveOutline = async (updatedOutline: ChapterOutline[]) => {
    if (!taskId) return;
    setIsLoading(true);
    setOutline(updatedOutline);

    try {
      await approveOutline(taskId, updatedOutline);
      setCurrentStep(3);
      setIsLoading(false);
    } catch (err: any) {
      setErrorMsg(err.message || '确认大纲失败');
      setIsLoading(false);
    }
  };

  // 4. 重置调研 (Bug 15: 前端 Reset 时向后端发送取消请求)
  const handleReset = () => {
    if (taskId && (currentStep === 2 || currentStep === 3)) {
      cancelTask(taskId).catch(() => {});
    }

    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }
    setCurrentStep(1);
    setTaskId(null);
    setOutline([]);
    setCitations([]);
    setLogs([]);
    setFinalReport('');
    setCriticFeedback('');
    setUploadedDocs([]);
    setIterationCount(1);
    setIsLoading(false);
    setErrorMsg(null);
  };

  // 5. 划词深挖
  const handleDeepDive = (selectedText: string) => {
    setDeepDiveQuestion(lang === 'zh' 
      ? `请结合研报，重点深入展开解析这一论述：「${selectedText}」`
      : `Please deep dive into this statement based on the report: "${selectedText}"`
    );
    setIsQAOpen(true);
  };

  // 6. 历史研报载入
  const handleSelectHistoryReport = (detail: any) => {
    if (!detail) return;
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }
    setTaskId(detail.task_id);
    setQuery(detail.user_query || '');
    setFinalReport(detail.final_report || '');
    setOutline(detail.outline || []);
    setCitations(detail.citations || []);
    setClarification(detail.summary || '');
    setLogs([`[Archive] Loaded historical research: "${detail.user_query}" (${detail.word_count || 0} characters)`]);
    setCurrentStep(4);
    setIsLoading(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // 7. 段落锚定平滑滚动与高亮
  const handleScrollToAnchor = (anchorText: string) => {
    const clean = anchorText.replace(/^[⚓\s*\[\]]+/, '').replace(/[\[\]]/g, '').trim();
    const headings = document.querySelectorAll('h1, h2, h3, h4');
    for (let i = 0; i < headings.length; i++) {
      const el = headings[i] as HTMLElement;
      if (el.innerText.includes(clean) || (clean.includes('执行摘要') && el.innerText.includes('执行摘要'))) {
        const yOffset = -80;
        const y = el.getBoundingClientRect().top + window.pageYOffset + yOffset;
        window.scrollTo({ top: y, behavior: 'smooth' });
        el.classList.remove('anchor-highlight-pulse');
        void el.offsetWidth;
        el.classList.add('anchor-highlight-pulse');
        setTimeout(() => el.classList.remove('anchor-highlight-pulse'), 2600);
        break;
      }
    }
  };

  return (
    <div className="min-h-screen flex flex-col relative transition-colors duration-300">
      
      {/* 背景环境光晕 */}
      <div 
        className="fixed top-0 left-1/4 w-96 h-96 rounded-full blur-[128px] pointer-events-none -z-10"
        style={{ backgroundColor: 'var(--glow-1)' }}
      />
      <div 
        className="fixed bottom-0 right-1/4 w-96 h-96 rounded-full blur-[128px] pointer-events-none -z-10"
        style={{ backgroundColor: 'var(--glow-2)' }}
      />

      {/* 顶部导航栏 (含历史研报库、语言切换、主题切换与自定义模型配置) */}
      <Navbar
        currentStep={currentStep}
        onReset={handleReset}
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenModelSettings={() => setIsModelSettingsOpen(true)}
        hasCustomModel={!!(customLLMConfig?.api_key || customLLMConfig?.base_url || customLLMConfig?.model_name)}
        currentTheme={theme}
        onThemeChange={setTheme}
        currentLang={lang}
        onLangChange={setLang}
        isLive={currentStep === 3}
      />

      {/* 错误提示浮条 */}
      {errorMsg && (
        <div className="max-w-4xl mx-auto w-full px-4 mt-4">
          <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-xs p-3 rounded-xl flex items-center justify-between">
            <span>⚠️ {errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="opacity-70 hover:opacity-100">✕</button>
          </div>
        </div>
      )}

      {/* 核心步骤视图路由 */}
      <main className="flex-1 w-full">
        {currentStep === 1 && (
          <CommandHero
            onSubmit={handleStartResearch}
            isLoading={isLoading}
            currentLang={lang}
          />
        )}

        {currentStep === 2 && (
          <OutlineCanvas
            outline={outline}
            clarification={clarification}
            onApprove={handleApproveOutline}
            isLoading={isLoading}
            currentLang={lang}
            localDocs={uploadedDocs}
          />
        )}

        {currentStep === 3 && (
          <BentoRadarDashboard
            logs={logs}
            citations={citations}
            outline={outline}
            criticFeedback={criticFeedback}
            currentStep="research"
            iterationCount={iterationCount}
            maxIterations={maxIterations}
            taskId={taskId || undefined}
            currentLang={lang}
          />
        )}

        {currentStep === 4 && (
          <ReportViewer
            report={finalReport}
            citations={citations}
            outline={outline}
            taskId={taskId || undefined}
            onOpenQA={(q) => {
              if (q) setDeepDiveQuestion(q);
              setIsQAOpen(true);
            }}
            onOpenExport={() => setIsExportOpen(true)}
            onOpenMindmap={() => setIsMindmapOpen(true)}
            onDeepDive={handleDeepDive}
            currentLang={lang}
            currentTheme={theme}
          />
        )}
      </main>

      {/* 追问抽屉 */}
      <FollowUpDrawer
        isOpen={isQAOpen}
        onClose={() => {
          setIsQAOpen(false);
          setDeepDiveQuestion('');
        }}
        report={finalReport}
        citations={citations}
        initialQuestion={deepDiveQuestion}
        onAnchorClick={handleScrollToAnchor}
        currentLang={lang}
      />

      {/* 历史研报抽屉 */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectReport={handleSelectHistoryReport}
        currentLang={lang}
      />

      {/* 导出弹窗 */}
      <ExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        report={finalReport}
        topic={query}
        outline={outline}
        taskId={taskId || undefined}
        currentLang={lang}
      />

      {/* 交互式思维导图弹窗 */}
      <MindmapModal
        isOpen={isMindmapOpen}
        onClose={() => setIsMindmapOpen(false)}
        report={finalReport}
        outline={outline}
        topic={query}
        currentLang={lang}
      />

      {/* 自定义模型网关配置弹窗 */}
      <ModelSettingsModal
        isOpen={isModelSettingsOpen}
        onClose={() => setIsModelSettingsOpen(false)}
        currentLang={lang}
        onConfigSaved={(cfg) => setCustomLLMConfig(cfg)}
      />

    </div>
  );
};

export default App;
