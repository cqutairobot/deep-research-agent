import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  Trash2, 
  CheckCircle, 
  Sparkles, 
  AlertCircle, 
  GripVertical, 
  ArrowUp, 
  ArrowDown, 
  Tag, 
  X,
  PlusCircle,
  FileText
} from 'lucide-react';
import { ChapterOutline } from '../types';
import { Language, translations } from '../locales/translations';

interface OutlineCanvasProps {
  outline: ChapterOutline[];
  clarification?: string;
  onApprove: (updatedOutline: ChapterOutline[]) => void;
  isLoading: boolean;
  currentLang?: Language;
  localDocs?: any[];
}

export const OutlineCanvas: React.FC<OutlineCanvasProps> = ({
  outline: initialOutline,
  clarification,
  onApprove,
  isLoading,
  currentLang = 'zh',
  localDocs = []
}) => {
  const t = translations[currentLang].outline;
  const [chapters, setChapters] = useState<ChapterOutline[]>(initialOutline);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [newQueryInputs, setNewQueryInputs] = useState<Record<number, string>>({});
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const handleToggleBoundDoc = (chapterIndex: number, fileName: string) => {
    const updated = [...chapters];
    const currentBound = [...(updated[chapterIndex].bound_documents || [])];
    const bIdx = currentBound.indexOf(fileName);
    if (bIdx >= 0) {
      currentBound.splice(bIdx, 1);
    } else {
      currentBound.push(fileName);
    }
    updated[chapterIndex] = {
      ...updated[chapterIndex],
      bound_documents: currentBound
    };
    setChapters(updated);
  };

  // 同步外部 initialOutline 属性变化
  useEffect(() => {
    if (initialOutline && initialOutline.length > 0) {
      setChapters(initialOutline);
    }
  }, [initialOutline]);

  const handleUpdate = (index: number, field: 'title' | 'focus', value: string) => {
    setValidationError(null);
    const updated = [...chapters];
    updated[index] = { ...updated[index], [field]: value };
    setChapters(updated);
  };

  // 检索词 Tag 管理
  const handleAddQuery = (index: number, queryText?: string) => {
    const text = (queryText || newQueryInputs[index] || '').trim();
    if (!text) return;
    setValidationError(null);
    const updated = [...chapters];
    const currentQueries = updated[index].search_queries || [];
    if (!currentQueries.includes(text)) {
      updated[index] = {
        ...updated[index],
        search_queries: [...currentQueries, text]
      };
      setChapters(updated);
    }
    setNewQueryInputs(prev => ({ ...prev, [index]: '' }));
  };

  const handleRemoveQuery = (chapterIndex: number, queryIndex: number) => {
    const updated = [...chapters];
    const currentQueries = [...(updated[chapterIndex].search_queries || [])];
    currentQueries.splice(queryIndex, 1);
    updated[chapterIndex] = {
      ...updated[chapterIndex],
      search_queries: currentQueries
    };
    setChapters(updated);
  };

  const handleAddChapter = () => {
    setValidationError(null);
    const newNum = chapters.length + 1;
    setChapters([
      ...chapters,
      {
        chapter_num: newNum,
        title: t.newChapterTitle,
        focus: t.newChapterFocus,
        search_queries: [t.newChapterQuery],
        extracted_facts: []
      }
    ]);
  };

  const handleDeleteChapter = (index: number) => {
    setValidationError(null);
    if (chapters.length <= 1) {
      alert(t.minChapterAlert);
      return;
    }
    const filtered = chapters.filter((_, i) => i !== index);
    const reindexed = filtered.map((ch, i) => ({ ...ch, chapter_num: i + 1 }));
    setChapters(reindexed);
  };

  // 章节上下移动与重排
  const handleMoveChapter = (fromIndex: number, toIndex: number) => {
    if (toIndex < 0 || toIndex >= chapters.length) return;
    const updated = [...chapters];
    const [moved] = updated.splice(fromIndex, 1);
    updated.splice(toIndex, 0, moved);
    const reindexed = updated.map((ch, i) => ({ ...ch, chapter_num: i + 1 }));
    setChapters(reindexed);
  };

  // 拖拽排序事件
  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;
    handleMoveChapter(draggedIndex, index);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  const handleApproveClick = () => {
    if (!chapters || chapters.length === 0) {
      setValidationError(currentLang === 'zh' ? '大纲至少需包含 1 个章节' : 'At least 1 chapter is required');
      return;
    }

    for (let i = 0; i < chapters.length; i++) {
      const ch = chapters[i];
      if (!ch.title || ch.title.trim().length < 2) {
        setValidationError(currentLang === 'zh' ? `第 ${i + 1} 章标题不能为空或少于 2 个字符` : `Chapter ${i + 1} title cannot be empty`);
        return;
      }
      if (!ch.focus || ch.focus.trim().length < 2) {
        setValidationError(currentLang === 'zh' ? `第 ${i + 1} 章调研侧重点不能为空或少于 2 个字符` : `Chapter ${i + 1} focus cannot be empty`);
        return;
      }
    }

    setValidationError(null);
    onApprove(chapters);
  };

  // 生成 AI 建议拓展词
  const getAISuggestedQueries = (ch: ChapterOutline): string[] => {
    const base = ch.title.replace(/^第\s*\d+\s*章[:：]?\s*/, '').replace(/概述|分析|研究|对比/, '').trim();
    const suggestions = [
      `${base} 核心技术机理`,
      `${base} 主流厂商量产进展`,
      `${base} 产业化痛点与成本测算`
    ];
    const existing = new Set(ch.search_queries || []);
    return suggestions.filter(s => !existing.has(s)).slice(0, 2);
  };

  return (
    <div className="max-w-4xl mx-auto w-full py-6 px-4 sm:px-6 space-y-6">
      
      {/* 状态通知栏 */}
      <div className="theme-surface rounded-2xl p-5 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="text-xs theme-accent-text font-mono font-medium flex items-center gap-1.5 mb-1">
            <Sparkles className="w-3.5 h-3.5" />
            <span>{t.statusBadge}</span>
          </div>
          <h2 className="text-lg font-bold flex items-center gap-2">
            <span>{t.title}</span>
            <span className="text-xs bg-amber-500/15 text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-full border border-amber-500/30 font-sans">
              {t.hitlBadge}
            </span>
          </h2>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleAddChapter}
            className="px-3.5 py-2 rounded-xl theme-card opacity-90 hover:opacity-100 text-xs font-medium flex items-center gap-1.5 transition cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5 theme-accent-text" />
            <span>{t.addChapter}</span>
          </button>
          
          <button
            type="button"
            onClick={handleApproveClick}
            disabled={isLoading}
            className="px-5 py-2 rounded-xl theme-btn-primary text-xs font-semibold shadow-lg flex items-center gap-2 transition cursor-pointer"
          >
            <CheckCircle className="w-4 h-4" />
            <span>{isLoading ? t.approvingBtn : t.approveBtn}</span>
          </button>
        </div>
      </div>

      {/* 校验错误提示 */}
      {validationError && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-xs p-3 rounded-xl flex items-center justify-between animate-in fade-in">
          <span>⚠️ {validationError}</span>
          <button type="button" onClick={() => setValidationError(null)} aria-label="Dismiss error" className="opacity-70 hover:opacity-100">✕</button>
        </div>
      )}

      {/* 智能澄清卡片 */}
      {clarification && (
        <div className="theme-nested rounded-xl p-4 text-xs flex items-start gap-3">
          <AlertCircle className="w-4 h-4 theme-accent-text shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold theme-accent-text">{t.clarificationTitle}</span>
            <p className="opacity-80 leading-relaxed">{clarification}</p>
          </div>
        </div>
      )}

      {/* 可拖拽 & 检索词标签化编辑大纲卡片列表 */}
      <div className="space-y-4">
        {chapters.map((ch, idx) => {
          const aiSuggestions = getAISuggestedQueries(ch);
          return (
            <div
              key={idx}
              draggable
              onDragStart={(e) => handleDragStart(e, idx)}
              onDragOver={(e) => handleDragOver(e, idx)}
              onDragEnd={handleDragEnd}
              className={`theme-card rounded-2xl p-4 space-y-3.5 group shadow-sm transition-all border ${
                draggedIndex === idx ? 'opacity-50 border-blue-500 scale-[0.99]' : 'hover:border-subtle'
              }`}
            >
              {/* 卡片头部：拖拽手柄 + 序号 + 标题 + 上下排序 + 删除 */}
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 flex-1">
                  <div 
                    className="opacity-40 hover:opacity-90 cursor-grab active:cursor-grabbing p-1 rounded hover:theme-nested"
                    title="按住鼠标拖拽调整章节顺序"
                  >
                    <GripVertical className="w-4 h-4" />
                  </div>
                  
                  <span className="w-7 h-7 rounded-lg theme-badge font-mono text-xs font-bold flex items-center justify-center shrink-0">
                    0{ch.chapter_num}
                  </span>

                  <input
                    type="text"
                    value={ch.title}
                    onChange={(e) => handleUpdate(idx, 'title', e.target.value)}
                    className="flex-1 bg-transparent text-sm font-semibold border-b border-transparent hover:border-subtle focus:border-subtle theme-nested rounded px-2 py-1 focus:outline-none transition"
                    placeholder="Chapter Title..."
                  />
                </div>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => handleMoveChapter(idx, idx - 1)}
                    disabled={idx === 0}
                    title="上移此章"
                    className="p-1 rounded opacity-40 hover:opacity-100 disabled:opacity-10 transition"
                  >
                    <ArrowUp className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMoveChapter(idx, idx + 1)}
                    disabled={idx === chapters.length - 1}
                    title="下移此章"
                    className="p-1 rounded opacity-40 hover:opacity-100 disabled:opacity-10 transition"
                  >
                    <ArrowDown className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteChapter(idx)}
                    aria-label={`Delete Chapter ${ch.chapter_num}`}
                    className="opacity-40 hover:opacity-100 hover:text-red-500 p-1.5 rounded-lg transition ml-1"
                    title="删除此章"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* 调研侧重点 */}
              <div className="pl-8">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] opacity-70 font-medium shrink-0">{t.focusLabel}</span>
                  <input
                    type="text"
                    value={ch.focus}
                    onChange={(e) => handleUpdate(idx, 'focus', e.target.value)}
                    className="flex-1 theme-nested rounded-lg px-2.5 py-1 text-xs focus:outline-none transition"
                    placeholder={t.focusPlaceholder}
                  />
                </div>

                {/* 规划检索词 Tag 编辑器 */}
                <div className="mt-3 pt-2.5 border-t border-subtle/50 space-y-2">
                  <div className="flex items-center justify-between text-[11px] opacity-70">
                    <span className="flex items-center gap-1 font-medium">
                      <Tag className="w-3 h-3 theme-accent-text" />
                      <span>{t.queriesLabel}</span>
                    </span>
                    <span className="text-[10px] opacity-60">按回车新增检索词</span>
                  </div>

                  {/* 标签列表与添加输入框 */}
                  <div className="flex flex-wrap items-center gap-1.5">
                    {(ch.search_queries || []).map((q, qIdx) => (
                      <span
                        key={qIdx}
                        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg theme-nested text-[11px] font-mono border border-subtle/60 shadow-xs"
                      >
                        <span>{q}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveQuery(idx, qIdx)}
                          className="opacity-50 hover:opacity-100 hover:text-red-500 transition"
                        >
                          <X className="w-2.5 h-2.5" />
                        </button>
                      </span>
                    ))}

                    <div className="inline-flex items-center gap-1">
                      <input
                        type="text"
                        value={newQueryInputs[idx] || ''}
                        onChange={(e) => setNewQueryInputs(prev => ({ ...prev, [idx]: e.target.value }))}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleAddQuery(idx);
                          }
                        }}
                        placeholder="+ 新增检索词..."
                        className="text-[11px] px-2 py-0.5 rounded-lg theme-nested border border-dashed border-subtle focus:outline-none focus:border-blue-500 min-w-[120px]"
                      />
                      {newQueryInputs[idx] && (
                        <button
                          type="button"
                          onClick={() => handleAddQuery(idx)}
                          className="p-1 rounded theme-btn-primary text-white text-[10px]"
                        >
                          <PlusCircle className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* ✨ AI 拓展建议词 */}
                  {aiSuggestions.length > 0 && (
                    <div className="flex items-center gap-1.5 pt-1 text-[10px] opacity-70">
                      <Sparkles className="w-3 h-3 theme-accent-text shrink-0" />
                      <span className="opacity-80">推荐拓展词:</span>
                      <div className="flex flex-wrap gap-1">
                        {aiSuggestions.map((sug, sIdx) => (
                          <button
                            key={sIdx}
                            type="button"
                            onClick={() => handleAddQuery(idx, sug)}
                            className="px-2 py-0.5 rounded-md theme-nested opacity-90 hover:opacity-100 hover:border-blue-500 text-[10px] border border-subtle/40 transition cursor-pointer flex items-center gap-1"
                          >
                            <span>+ {sug}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 📄 章节专属私有文档绑定 */}
                  {localDocs && localDocs.length > 0 && (
                    <div className="pt-2 border-t border-subtle/40 flex flex-wrap items-center gap-2 text-[11px]">
                      <span className="text-[10px] font-semibold opacity-60 flex items-center gap-1 shrink-0">
                        <FileText className="w-3 h-3 theme-accent-text" />
                        <span>{currentLang === 'zh' ? '专属私有资料绑定:' : 'Bound Docs:'}</span>
                      </span>
                      <div className="flex flex-wrap gap-1.5 items-center">
                        {localDocs.map((doc: any, dIdx: number) => {
                          const fname = doc.file_name || `文档_${dIdx + 1}`;
                          const isBound = (ch.bound_documents || []).includes(fname);
                          return (
                            <button
                              key={dIdx}
                              type="button"
                              onClick={() => handleToggleBoundDoc(idx, fname)}
                              className={`px-2 py-0.5 rounded-lg text-[10px] font-medium transition cursor-pointer flex items-center gap-1 border ${
                                isBound
                                  ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/50 shadow-xs'
                                  : 'theme-nested opacity-60 hover:opacity-100 border-subtle/50'
                              }`}
                              title={isBound ? '点击取消绑定' : '点击将此文档绑定到本章（检索时大幅提高优先级）'}
                            >
                              <span>{fname}</span>
                              {isBound && <span className="text-[9px] font-bold">✓</span>}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                </div>
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
};
