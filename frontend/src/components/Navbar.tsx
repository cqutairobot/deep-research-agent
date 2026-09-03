import React from 'react';
import { Sparkles, CheckCircle2, RotateCcw, Activity, FolderClock, Cpu } from 'lucide-react';
import { ThemeSelector, ThemeType } from './ThemeSelector';
import { LanguageSelector } from './LanguageSelector';
import { Language, translations } from '../locales/translations';

interface NavbarProps {
  currentStep: number;
  onReset: () => void;
  onOpenHistory?: () => void;
  onOpenModelSettings?: () => void;
  hasCustomModel?: boolean;
  currentTheme: ThemeType;
  onThemeChange: (theme: ThemeType) => void;
  currentLang: Language;
  onLangChange: (lang: Language) => void;
  statusText?: string;
  isLive?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentStep,
  onReset,
  onOpenHistory,
  onOpenModelSettings,
  hasCustomModel,
  currentTheme,
  onThemeChange,
  currentLang,
  onLangChange,
  statusText,
  isLive
}) => {
  const t = translations[currentLang].nav;

  const steps = [
    { num: 1, label: t.step1 },
    { num: 2, label: t.step2 },
    { num: 3, label: t.step3 },
    { num: 4, label: t.step4 }
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-subtle theme-surface">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        
        {/* Logo 与产品标识 */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl theme-btn-primary flex items-center justify-center text-white shadow-lg ring-1 ring-white/20">
            <Sparkles className="w-5 h-5 text-white animate-pulse-subtle" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm sm:text-base tracking-tight">{t.title}</span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded theme-badge font-semibold">{t.version}</span>
            </div>
            <div className="text-[11px] opacity-70 font-sans hidden sm:block">{t.subtitle}</div>
          </div>
        </div>

        {/* 步骤流指示器 */}
        <div className="hidden md:flex items-center gap-2 theme-nested rounded-full px-3 py-1.5 shadow-inner">
          {steps.map((step, idx) => {
            const isActive = currentStep === step.num;
            const isDone = currentStep > step.num;
            return (
              <React.Fragment key={step.num}>
                <div className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full transition-all duration-300 ${
                  isActive
                    ? 'theme-pill-active font-medium shadow-md'
                    : isDone
                    ? 'text-emerald-600 dark:text-emerald-400 font-medium'
                    : 'opacity-60'
                }`}>
                  {isDone ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                  ) : (
                    <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] ${
                      isActive ? 'bg-white/20 text-white' : 'theme-nested'
                    }`}>
                      {step.num}
                    </span>
                  )}
                  <span>{step.label}</span>
                </div>
                {idx < steps.length - 1 && (
                  <div className="w-3 h-px opacity-20 bg-current" />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* 右侧操作区：语言切换 + 主题切换 + 新建调研 */}
        <div className="flex items-center gap-2.5">
          {isLive && (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              <Activity className="w-3.5 h-3.5" />
              <span>{t.liveSse}</span>
            </div>
          )}

          {/* 语言选择器 */}
          <LanguageSelector
            currentLang={currentLang}
            onLangChange={onLangChange}
          />

          {/* 主题切换器 */}
          <ThemeSelector
            currentTheme={currentTheme}
            onThemeChange={onThemeChange}
            currentLang={currentLang}
          />

          {/* 自定义模型配置按钮 */}
          {onOpenModelSettings && (
            <button
              type="button"
              onClick={onOpenModelSettings}
              title={currentLang === 'zh' ? '配置自定义大模型 (OpenAI/Claude)' : 'Configure Custom LLM'}
              className="relative flex items-center gap-1.5 text-xs opacity-85 hover:opacity-100 px-3 py-2 rounded-xl border theme-card transition shadow-sm cursor-pointer min-h-[36px] sm:min-h-[auto]"
            >
              <Cpu className={`w-3.5 h-3.5 ${hasCustomModel ? 'text-blue-500' : 'theme-accent-text'}`} />
              <span className="hidden sm:inline">{t.modelSettings || (currentLang === 'zh' ? '模型配置' : 'Model Gateway')}</span>
              {hasCustomModel && (
                <span className="w-2 h-2 rounded-full bg-blue-500 ring-2 ring-blue-500/20 animate-pulse" />
              )}
            </button>
          )}

          {/* 历史研报库按钮 */}
          {onOpenHistory && (
            <button
              type="button"
              onClick={onOpenHistory}
              title={currentLang === 'zh' ? '查看历史研报归档' : 'View History Reports'}
              className="flex items-center gap-1.5 text-xs opacity-85 hover:opacity-100 px-3 py-2 rounded-xl border theme-card transition shadow-sm cursor-pointer min-h-[36px] sm:min-h-[auto]"
            >
              <FolderClock className="w-3.5 h-3.5 theme-accent-text" />
              <span className="hidden sm:inline">{currentLang === 'zh' ? '历史研报' : 'History'}</span>
            </button>
          )}

          <button
            type="button"
            onClick={onReset}
            aria-label={t.newResearch}
            title={t.newResearch}
            className="flex items-center gap-1.5 text-xs opacity-80 hover:opacity-100 px-3 py-2 rounded-xl border theme-card transition shadow-sm cursor-pointer min-h-[36px] sm:min-h-[auto]"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{t.newResearch}</span>
          </button>
        </div>

      </div>
    </header>
  );
};
