import React, { useState } from 'react';
import { Plus, Trash2, CheckCircle, Sparkles, AlertCircle } from 'lucide-react';
import { ChapterOutline } from '../types';
import { Language, translations } from '../locales/translations';

interface OutlineCanvasProps {
  outline: ChapterOutline[];
  clarification?: string;
  onApprove: (updatedOutline: ChapterOutline[]) => void;
  isLoading: boolean;
  currentLang?: Language;
}

export const OutlineCanvas: React.FC<OutlineCanvasProps> = ({
  outline: initialOutline,
  clarification,
  onApprove,
  isLoading,
  currentLang = 'zh'
}) => {
  const t = translations[currentLang].outline;
  const [chapters, setChapters] = useState<ChapterOutline[]>(initialOutline);

  const handleUpdate = (index: number, field: 'title' | 'focus', value: string) => {
    const updated = [...chapters];
    updated[index] = { ...updated[index], [field]: value };
    setChapters(updated);
  };

  const handleAddChapter = () => {
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
    if (chapters.length <= 1) {
      alert(t.minChapterAlert);
      return;
    }
    const filtered = chapters.filter((_, i) => i !== index);
    const reindexed = filtered.map((ch, i) => ({ ...ch, chapter_num: i + 1 }));
    setChapters(reindexed);
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
            onClick={() => onApprove(chapters)}
            disabled={isLoading}
            className="px-5 py-2 rounded-xl theme-btn-primary text-xs font-semibold shadow-lg flex items-center gap-2 transition cursor-pointer"
          >
            <CheckCircle className="w-4 h-4" />
            <span>{isLoading ? t.approvingBtn : t.approveBtn}</span>
          </button>
        </div>
      </div>

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

      {/* 可编辑大纲卡片列表 */}
      <div className="space-y-3.5">
        {chapters.map((ch, idx) => (
          <div
            key={idx}
            className="theme-card rounded-xl p-4 space-y-3 group shadow-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 flex-1">
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
              <button
                type="button"
                onClick={() => handleDeleteChapter(idx)}
                className="opacity-50 hover:opacity-100 hover:text-red-500 p-1.5 rounded-lg transition"
                title="Delete"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            {/* 调研侧重点 */}
            <div className="pl-10">
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

              {/* 规划检索词 */}
              {ch.search_queries && ch.search_queries.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                  <span className="text-[10px] opacity-60">{t.queriesLabel}</span>
                  {ch.search_queries.map((q, qIdx) => (
                    <span
                      key={qIdx}
                      className="text-[10px] theme-nested px-2 py-0.5 rounded font-mono"
                    >
                      {q}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

    </div>
  );
};
