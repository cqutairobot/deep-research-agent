import React, { useState, useRef } from 'react';
import { 
  Sparkles, 
  ArrowRight, 
  Zap, 
  Search, 
  BookOpen, 
  Layers, 
  FileText, 
  Globe, 
  Upload, 
  FileUp, 
  X, 
  CheckCircle2,
  RefreshCw 
} from 'lucide-react';
import { uploadDocument, fetchRecommendedTopics, RecommendedTopic } from '../lib/api';
import { Language, translations } from '../locales/translations';
import { ReportStyle } from '../types';

interface CommandHeroProps {
  onSubmit: (
    query: string, 
    depth: 'quick' | 'standard' | 'deep', 
    style: ReportStyle,
    localDocs?: any[]
  ) => void;
  isLoading: boolean;
  currentLang?: Language;
}

export const CommandHero: React.FC<CommandHeroProps> = ({ 
  onSubmit, 
  isLoading,
  currentLang = 'zh'
}) => {
  const t = translations[currentLang].hero;
  const [query, setQuery] = useState('');
  const [depth, setDepth] = useState<'quick' | 'standard' | 'deep'>('standard');
  const [style, setStyle] = useState<ReportStyle>('consulting');
  const [uploadedFiles, setUploadedFiles] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [presets, setPresets] = useState<RecommendedTopic[]>(t.presets);
  const [isRefreshingPresets, setIsRefreshingPresets] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 切换语言时重置
  React.useEffect(() => {
    setPresets(t.presets);
  }, [currentLang]);

  // 调用大模型或多元题库换一批推荐课题
  const handleRefreshPresets = async () => {
    if (isRefreshingPresets) return;
    setIsRefreshingPresets(true);
    try {
      let customLLMCfg = null;
      const savedConfig = localStorage.getItem('deep_research_custom_llm');
      if (savedConfig) {
        try {
          customLLMCfg = JSON.parse(savedConfig);
        } catch {}
      }
      const newTopics = await fetchRecommendedTopics(customLLMCfg, 4);
      if (newTopics && newTopics.length > 0) {
        setPresets(newTopics);
      }
    } catch (e) {
      console.warn('刷新精选课题失败:', e);
    } finally {
      setIsRefreshingPresets(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        const parsed = await uploadDocument(file);
        setUploadedFiles(prev => [...prev, parsed]);
      } catch (err: any) {
        alert(`${currentLang === 'zh' ? '上传失败' : 'Upload failed'}: ${err.message}`);
      }
    }
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || isLoading) return;
    onSubmit(query.trim(), depth, style, uploadedFiles);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      handleSubmit();
    }
  };

  return (
    <div className="relative max-w-4xl mx-auto w-full pt-8 pb-12 px-4 sm:px-6">
      
      {/* 顶部标题 */}
      <div className="text-center space-y-3 mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full theme-badge text-xs font-medium tracking-wide">
          <Sparkles className="w-3.5 h-3.5" />
          <span>{t.badge}</span>
        </div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight leading-tight">
          {t.title}
        </h1>
        <p className="text-sm sm:text-base opacity-75 max-w-2xl mx-auto">
          {t.subtitle}
        </p>
      </div>

      {/* 核心命令控制台卡片 */}
      <div className="relative theme-surface rounded-2xl p-5 sm:p-7 shadow-2xl transition-all duration-300">
        
        {/* 输入框 */}
        <div className="relative mb-5">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={3}
            disabled={isLoading}
            placeholder={t.placeholder}
            className="w-full theme-input rounded-xl p-4 text-sm sm:text-base placeholder-opacity-40 focus:outline-none transition resize-none leading-relaxed"
          />
          <div className="absolute right-3 bottom-3 hidden sm:flex items-center gap-1.5 text-[11px] opacity-60 font-mono">
            <kbd className="px-1.5 py-0.5 rounded theme-nested text-xs">⌘</kbd>
            <span>+</span>
            <kbd className="px-1.5 py-0.5 rounded theme-nested text-xs">Enter</kbd>
            <span>{t.launchHint}</span>
          </div>
        </div>

        {/* 本地私有文档上传区域 */}
        <div className="mb-5 p-3.5 rounded-xl theme-nested border border-dashed border-subtle">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-xs">
              <FileUp className="w-4 h-4 theme-accent-text" />
              <span className="font-semibold">{t.localDocsTitle}</span>
              <span className="opacity-70 text-[11px]">{t.localDocsHint}</span>
            </div>
            
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              multiple
              accept=".pdf,.docx,.doc,.txt,.md"
              className="hidden"
            />
            
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="px-3 py-1 rounded-lg theme-card text-xs font-medium opacity-90 hover:opacity-100 flex items-center gap-1.5 transition cursor-pointer"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>{uploading ? t.uploading : t.uploadBtn}</span>
            </button>
          </div>

          {/* 已上传文件芯片列表 */}
          {uploadedFiles.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3 pt-2 border-t border-subtle/50">
              {uploadedFiles.map((doc, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg theme-card text-xs border border-subtle shadow-sm animate-in fade-in"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                  <span className="font-medium max-w-[160px] truncate">{doc.file_name}</span>
                  <span className="text-[10px] opacity-60 font-mono">({doc.chunk_count} {t.chunks})</span>
                  <button
                    type="button"
                    onClick={() => removeFile(idx)}
                    className="opacity-50 hover:opacity-100 p-0.5 hover:text-red-500 transition cursor-pointer"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 灵感预设芯片 */}
        <div className="mb-6">
          <div className="text-xs opacity-75 mb-2 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 theme-accent-text" />
              <span>{t.presetsTitle}</span>
            </div>
            <button
              type="button"
              onClick={handleRefreshPresets}
              disabled={isRefreshingPresets}
              className="flex items-center gap-1 text-[11px] theme-accent-text hover:brightness-125 transition cursor-pointer disabled:opacity-50 select-none py-0.5 px-1.5 rounded hover:bg-black/5 dark:hover:bg-white/5"
              title="调用大模型或前沿题材库，动态换一批研究课题"
            >
              <RefreshCw className={`w-3 h-3 ${isRefreshingPresets ? 'animate-spin text-cyan-400' : ''}`} />
              <span>{isRefreshingPresets ? (currentLang === 'zh' ? 'AI 构思中...' : 'Generating...') : (currentLang === 'zh' ? '换一批' : 'Refresh')}</span>
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {presets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setQuery(p.text)}
                className="text-xs theme-card opacity-90 hover:opacity-100 px-3 py-1.5 rounded-lg transition shadow-sm cursor-pointer hover:border-cyan-500/50 hover:scale-[1.02] active:scale-[0.98]"
                title={p.text}
              >
                {p.title}
              </button>
            ))}
          </div>
        </div>

        {/* 核心参数控制面板 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-5 border-t border-subtle mb-6">
          
          {/* 调研深度选择 */}
          <div>
            <label className="block text-xs font-medium opacity-80 mb-2 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 theme-accent-text" />
              <span>{t.depthLabel}</span>
            </label>
            <div className="grid grid-cols-3 gap-1.5 theme-nested p-1 rounded-xl">
              <button
                type="button"
                onClick={() => setDepth('quick')}
                className={`py-2 px-2 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1 cursor-pointer ${
                  depth === 'quick' ? 'theme-pill-active shadow-md' : 'opacity-70 hover:opacity-100'
                }`}
              >
                <Zap className="w-3 h-3" />
                <span>{t.depthQuick}</span>
              </button>
              <button
                type="button"
                onClick={() => setDepth('standard')}
                className={`py-2 px-2 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1 cursor-pointer ${
                  depth === 'standard' ? 'theme-pill-active shadow-md' : 'opacity-70 hover:opacity-100'
                }`}
              >
                <Search className="w-3 h-3" />
                <span>{t.depthStandard}</span>
              </button>
              <button
                type="button"
                onClick={() => setDepth('deep')}
                className={`py-2 px-2 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1 cursor-pointer ${
                  depth === 'deep' ? 'theme-pill-active shadow-md' : 'opacity-70 hover:opacity-100'
                }`}
              >
                <BookOpen className="w-3 h-3" />
                <span>{t.depthDeep}</span>
              </button>
            </div>
          </div>

          {/* 报告风格选择 */}
          <div>
            <label className="block text-xs font-medium opacity-80 mb-2 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 theme-accent-text" />
              <span>{t.styleLabel}</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5 theme-nested p-1 rounded-xl">
              <button
                type="button"
                onClick={() => setStyle('consulting')}
                className={`py-2 px-1 rounded-lg text-xs font-medium transition-all flex flex-col items-center justify-center gap-0.5 cursor-pointer ${
                  style === 'consulting' ? 'theme-pill-active shadow-md' : 'opacity-70 hover:opacity-100'
                }`}
              >
                <span className="font-medium">💼 {currentLang === 'zh' ? '商业咨询' : 'Consulting'}</span>
                <span className="text-[10px] opacity-60 scale-90">MECE / 厂商对比</span>
              </button>
              <button
                type="button"
                onClick={() => setStyle('literature_review')}
                className={`py-2 px-1 rounded-lg text-xs font-medium transition-all flex flex-col items-center justify-center gap-0.5 cursor-pointer ${
                  style === 'literature_review' || style === 'academic' ? 'theme-pill-active shadow-md' : 'opacity-70 hover:opacity-100'
                }`}
              >
                <span className="font-medium">📑 {currentLang === 'zh' ? '学术综述' : 'Literature'}</span>
                <span className="text-[10px] opacity-60 scale-90">分类学 / LaTeX</span>
              </button>
              <button
                type="button"
                onClick={() => setStyle('tutorial_docs')}
                className={`py-2 px-1 rounded-lg text-xs font-medium transition-all flex flex-col items-center justify-center gap-0.5 cursor-pointer ${
                  style === 'tutorial_docs' ? 'theme-pill-active shadow-md' : 'opacity-70 hover:opacity-100'
                }`}
              >
                <span className="font-medium">🛠️ {currentLang === 'zh' ? '技术教程' : 'Cookbook'}</span>
                <span className="text-[10px] opacity-60 scale-90">分步实操 / 代码</span>
              </button>
              <button
                type="button"
                onClick={() => setStyle('executive')}
                className={`py-2 px-1 rounded-lg text-xs font-medium transition-all flex flex-col items-center justify-center gap-0.5 cursor-pointer ${
                  style === 'executive' ? 'theme-pill-active shadow-md' : 'opacity-70 hover:opacity-100'
                }`}
              >
                <span className="font-medium">🎯 {currentLang === 'zh' ? '高管内参' : 'Executive'}</span>
                <span className="text-[10px] opacity-60 scale-90">BLUF / 一页纸</span>
              </button>
              <button
                type="button"
                onClick={() => setStyle('briefing')}
                className={`py-2 px-1 rounded-lg text-xs font-medium transition-all flex flex-col items-center justify-center gap-0.5 cursor-pointer col-span-2 sm:col-span-1 ${
                  style === 'briefing' ? 'theme-pill-active shadow-md' : 'opacity-70 hover:opacity-100'
                }`}
              >
                <span className="font-medium">⚡ {currentLang === 'zh' ? '前沿特稿' : 'Briefing'}</span>
                <span className="text-[10px] opacity-60 scale-90">时间线 / 利益博弈</span>
              </button>
            </div>
          </div>

        </div>

        {/* 启动操作按钮 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs opacity-70 font-sans">
            <Globe className="w-3.5 h-3.5 theme-accent-text" />
            <span>
              {uploadedFiles.length > 0 
                ? t.footerInfoHybrid.replace('{count}', String(uploadedFiles.length))
                : t.footerInfo}
            </span>
          </div>
          <button
            type="button"
            onClick={() => handleSubmit()}
            disabled={!query.trim() || isLoading}
            className="px-6 py-3 theme-btn-primary font-medium text-sm rounded-xl shadow-lg flex items-center gap-2 transition disabled:opacity-50 cursor-pointer"
          >
            <span>{isLoading ? t.submittingBtn : t.submitBtn}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

      </div>

    </div>
  );
};
