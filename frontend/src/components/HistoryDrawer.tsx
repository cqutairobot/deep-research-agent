import React, { useState, useEffect } from 'react';
import { 
  X, 
  FolderClock, 
  Search, 
  Trash2, 
  FileText, 
  ExternalLink, 
  Calendar, 
  Hash, 
  Sparkles,
  BookOpen,
  ArrowRight
} from 'lucide-react';
import { Language } from '../locales/translations';

interface HistoryItem {
  task_id: string;
  user_query: string;
  research_depth: string;
  report_style: string;
  created_at: number;
  word_count: number;
  summary?: string;
}

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectReport: (reportDetail: any) => void;
  currentLang?: Language;
}

export const HistoryDrawer: React.FC<HistoryDrawerProps> = ({
  isOpen,
  onClose,
  onSelectReport,
  currentLang = 'zh'
}) => {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const url = searchQuery.trim() 
        ? `/api/v1/research/history?q=${encodeURIComponent(searchQuery.trim())}`
        : '/api/v1/research/history';
      const resp = await fetch(url);
      if (resp.ok) {
        const data = await resp.json();
        setItems(data.items || []);
      }
    } catch (err) {
      console.error('Failed to fetch research history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchHistory();
    }
  }, [isOpen, searchQuery]);

  const handleLoadItem = async (taskId: string) => {
    setLoadingId(taskId);
    try {
      const resp = await fetch(`/api/v1/research/history/${taskId}`);
      if (resp.ok) {
        const data = await resp.json();
        onSelectReport(data);
        onClose();
      } else {
        alert(currentLang === 'zh' ? '加载历史研报失败：记录不存在或已被删除' : 'Failed to load report: Not found');
      }
    } catch (err) {
      alert(currentLang === 'zh' ? '网络错误，无法加载该历史研报' : 'Network error loading report');
    } finally {
      setLoadingId(null);
    }
  };

  const handleDeleteItem = async (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation();
    if (!confirm(currentLang === 'zh' ? '确定要删除这份历史研报记录吗？' : 'Are you sure you want to delete this report?')) {
      return;
    }
    setDeletingId(taskId);
    try {
      const resp = await fetch(`/api/v1/research/history/${taskId}`, { method: 'DELETE' });
      if (resp.ok) {
        setItems(prev => prev.filter(it => it.task_id !== taskId));
      }
    } catch (err) {
      alert(currentLang === 'zh' ? '删除失败' : 'Failed to delete');
    } finally {
      setDeletingId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* 半透明背景遮罩，支持点击关闭 */}
      <div 
        className="fixed inset-0 bg-black/40 backdrop-blur-xs z-50 animate-in fade-in duration-200" 
        onClick={onClose} 
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="history-drawer-title"
        className="fixed inset-y-0 right-0 z-50 w-full sm:w-[540px] theme-surface border-l border-subtle shadow-2xl flex flex-col animate-in slide-in-from-right duration-300"
      >
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-subtle">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg theme-badge flex items-center justify-center">
            <FolderClock className="w-4 h-4 theme-accent-text" />
          </div>
          <div>
            <h3 id="history-drawer-title" className="text-sm font-bold flex items-center gap-2">
              <span>{currentLang === 'zh' ? '历史研报归档库' : 'Historical Reports'}</span>
              <span className="text-[10px] theme-nested px-2 py-0.5 rounded-full font-mono">
                {items.length} 篇
              </span>
            </h3>
            <p className="text-[11px] opacity-70">
              {currentLang === 'zh' ? '本地 SQLite 离线持久化归档，随时回看与二次追问' : 'Locally persisted in SQLite archive'}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close history drawer"
          className="opacity-70 hover:opacity-100 p-1.5 rounded-lg theme-nested transition cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* 搜索框 */}
      <div className="p-3.5 border-b border-subtle theme-nested">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 opacity-50" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={currentLang === 'zh' ? '搜索历史研报课题...' : 'Search reports...'}
            className="w-full theme-input rounded-xl pl-9 pr-3.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/30 transition"
          />
        </div>
      </div>

      {/* 列表内容 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {loading && items.length === 0 && (
          <div className="py-12 text-center text-xs opacity-60 flex items-center justify-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
            <span>{currentLang === 'zh' ? '正在读取历史归档...' : 'Loading history...'}</span>
          </div>
        )}

        {!loading && items.length === 0 && (
          <div className="py-16 text-center text-xs opacity-60 space-y-2">
            <BookOpen className="w-8 h-8 mx-auto opacity-40 mb-2" />
            <p className="font-semibold">{currentLang === 'zh' ? '暂无历史研报记录' : 'No historical reports yet'}</p>
            <p className="text-[11px] opacity-75">
              {currentLang === 'zh' ? '发起并完成深度调研后，系统将自动归档在此' : 'Completed research tasks will automatically appear here'}
            </p>
          </div>
        )}

        {items.map((item) => {
          const dateStr = item.created_at ? new Date(item.created_at * 1000).toLocaleString() : '';
          const depthLabel = item.research_depth === 'deep' ? '穷尽' : (item.research_depth === 'quick' ? '快速' : '标准');
          return (
            <div
              key={item.task_id}
              onClick={() => handleLoadItem(item.task_id)}
              className="theme-card rounded-2xl p-4 space-y-2.5 hover:border-blue-500/50 transition cursor-pointer border border-subtle shadow-sm group"
            >
              <div className="flex items-start justify-between gap-2">
                <h4 className="text-xs font-bold leading-snug group-hover:text-blue-500 transition line-clamp-2">
                  {item.user_query}
                </h4>
                <button
                  type="button"
                  onClick={(e) => handleDeleteItem(e, item.task_id)}
                  disabled={deletingId === item.task_id}
                  title="删除记录"
                  className="opacity-40 hover:opacity-100 hover:text-red-500 p-1 rounded-md transition shrink-0"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              {item.summary && (
                <p className="text-[11px] opacity-75 line-clamp-2 leading-relaxed">
                  {item.summary}
                </p>
              )}

              <div className="flex items-center justify-between text-[10px] opacity-70 pt-2 border-t border-subtle/50">
                <div className="flex items-center gap-2">
                  <span className="theme-nested px-1.5 py-0.5 rounded font-mono">
                    {depthLabel}深度
                  </span>
                  <span className="flex items-center gap-1 font-mono">
                    <Hash className="w-2.5 h-2.5" />
                    <span>{item.word_count.toLocaleString()} 字</span>
                  </span>
                  <span className="flex items-center gap-1 hidden sm:flex">
                    <Calendar className="w-2.5 h-2.5" />
                    <span>{dateStr}</span>
                  </span>
                </div>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleLoadItem(item.task_id);
                  }}
                  disabled={loadingId === item.task_id}
                  className="px-2.5 py-1 rounded-lg theme-btn-primary text-white text-[11px] font-medium flex items-center gap-1 transition shadow-xs hover:opacity-90 cursor-pointer"
                >
                  {loadingId === item.task_id ? (
                    <>
                      <span className="w-2.5 h-2.5 rounded-full border-2 border-white border-t-transparent animate-spin" />
                      <span>{currentLang === 'zh' ? '载入中...' : 'Loading...'}</span>
                    </>
                  ) : (
                    <>
                      <BookOpen className="w-3 h-3" />
                      <span>{currentLang === 'zh' ? '查看研报' : 'Open'}</span>
                      <ArrowRight className="w-2.5 h-2.5 opacity-70" />
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      </div>
    </>
  );
};
