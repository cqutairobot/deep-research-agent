import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { CommandHero } from './components/CommandHero';
import { OutlineCanvas } from './components/OutlineCanvas';
import { BentoRadarDashboard } from './components/BentoRadarDashboard';
import { ReportViewer } from './components/ReportViewer';
import { FollowUpDrawer } from './components/FollowUpDrawer';
import { ExportModal } from './components/ExportModal';
import { MindmapModal } from './components/MindmapModal';
import { ThemeType } from './components/ThemeSelector';
import { Language } from './locales/translations';
import { ChapterOutline, CitationSource, TaskStatus } from './types';
import { createTask, approveOutline, subscribeToTaskStream } from './lib/api';

export const App: React.FC = () => {
  // 主题配色状态 (持久化到 localStorage)
  const [theme, setTheme] = useState<ThemeType>(() => {
    return (localStorage.getItem('app-theme') as ThemeType) || 'vintage';
  });

  // 国际化语言状态 (持久化到 localStorage)
  const [lang, setLang] = useState<Language>(() => {
    return (localStorage.getItem('app-lang') as Language) || 'zh';
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
  
  // 弹窗与抽屉
  const [isQAOpen, setIsQAOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isMindmapOpen, setIsMindmapOpen] = useState(false);
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

  // 1. 发起调研任务 (支持本地文档混合 RAG)
  const handleStartResearch = async (
    userQuery: string,
    depth: 'quick' | 'standard' | 'deep',
    style: 'consulting' | 'academic' | 'executive',
    localDocs?: any[]
  ) => {
    setIsLoading(true);
    setErrorMsg(null);
    setQuery(userQuery);
    setLogs([`[System] Initializing research task: "${userQuery}" (${localDocs?.length || 0} local documents)...`]);
    
    const maxIter = depth === 'quick' ? 1 : (depth === 'deep' ? 3 : 2);
    setMaxIterations(maxIter);

    try {
      const res = await createTask(userQuery, depth, style, false, maxIter, localDocs);
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
        if (data.final_report) {
          setFinalReport(data.final_report);
          if (data.citations) setCitations(data.citations);
          setCurrentStep(4);
          setIsLoading(false);
        }
        break;

      case 'error':
        setErrorMsg(data.error || '任务执行发生异常');
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

  // 4. 重置调研
  const handleReset = () => {
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

      {/* 顶部导航栏 (含中英文语言切换与主题切换) */}
      <Navbar
        currentStep={currentStep}
        onReset={handleReset}
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
            currentLang={lang}
          />
        )}

        {currentStep === 4 && (
          <ReportViewer
            report={finalReport}
            citations={citations}
            outline={outline}
            onOpenQA={(q) => {
              if (q) setDeepDiveQuestion(q);
              setIsQAOpen(true);
            }}
            onOpenExport={() => setIsExportOpen(true)}
            onOpenMindmap={() => setIsMindmapOpen(true)}
            onDeepDive={handleDeepDive}
            currentLang={lang}
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
        currentLang={lang}
      />

      {/* 导出弹窗 */}
      <ExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        report={finalReport}
        topic={query}
        outline={outline}
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

    </div>
  );
};

export default App;
