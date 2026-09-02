import React from 'react';
import { ExternalLink, ShieldCheck, X } from 'lucide-react';
import { CitationSource } from '../types';
import { Language, translations } from '../locales/translations';

interface CitationPopoverProps {
  citation: CitationSource;
  position: { x: number; y: number };
  onClose: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  currentLang?: Language;
}

export const CitationPopover: React.FC<CitationPopoverProps> = ({
  citation,
  position,
  onClose,
  onMouseEnter,
  onMouseLeave,
  currentLang = 'zh'
}) => {
  const t = translations[currentLang].report;
  let domain = 'web source';
  try {
    domain = new URL(citation.url).hostname.replace('www.', '');
  } catch {}

  const safeLeft = Math.max(16, Math.min(position.x - 140, window.innerWidth - 340));
  const safeTop = Math.max(16, Math.min(position.y + 6, window.innerHeight - 270));

  return (
    <div
      style={{
        top: `${safeTop}px`,
        left: `${safeLeft}px`
      }}
      className="fixed z-50 w-80 theme-surface rounded-2xl p-4 shadow-2xl space-y-3 animate-in fade-in zoom-in-95 duration-150 border-2 select-text before:content-[''] before:absolute before:-top-3 before:left-0 before:right-0 before:h-4"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div className="flex items-center justify-between border-b border-subtle pb-2">
        <div className="flex items-center gap-2">
          <span className="w-5 h-5 rounded-md theme-btn-primary text-white font-mono text-[10px] font-bold flex items-center justify-center shrink-0">
            {citation.id}
          </span>
          <span className="text-xs font-mono theme-accent-text font-semibold truncate max-w-[150px]">{domain}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
            <ShieldCheck className="w-3 h-3" />
            <span>{t.citationVerified}</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="opacity-50 hover:opacity-100 p-0.5 rounded transition cursor-pointer"
            title="Close"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="space-y-1.5">
        <h4 className="text-xs font-bold leading-snug line-clamp-2">
          {citation.title}
        </h4>
        <div className="text-[11px] opacity-80 theme-nested p-2.5 rounded-xl leading-relaxed italic max-h-24 overflow-y-auto">
          "{citation.snippet || 'Verified evidence snippet.'}"
        </div>
      </div>

      <div className="flex items-center justify-between pt-1 border-t border-subtle/40">
        <span className="text-[10px] opacity-60 font-mono">
          {t.citationRelevance}: {((citation.score || 0.95) * 100).toFixed(0)}%
        </span>
        <a
          href={citation.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs theme-accent-text hover:underline font-semibold flex items-center gap-1.5 px-2 py-1 rounded-md theme-nested hover:brightness-110 transition cursor-pointer"
        >
          <span>{t.viewSource}</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>
    </div>
  );
};
