import React, { useState, useRef, useEffect } from 'react';
import { Globe, Check } from 'lucide-react';
import { Language } from '../locales/translations';

interface LanguageSelectorProps {
  currentLang: Language;
  onLangChange: (lang: Language) => void;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  currentLang,
  onLangChange
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg theme-card text-xs opacity-90 hover:opacity-100 transition shadow-sm cursor-pointer"
        title="切换语言 / Switch Language"
      >
        <Globe className="w-3.5 h-3.5 theme-accent-text" />
        <span className="font-medium font-mono">{currentLang === 'zh' ? '中 / CN' : 'EN'}</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-36 theme-surface rounded-xl p-1.5 shadow-2xl border border-subtle z-50 animate-in fade-in zoom-in-95 duration-150">
          <div className="text-[10px] opacity-60 px-2 py-1 font-mono uppercase">
            Language / 语言
          </div>
          
          <button
            type="button"
            onClick={() => {
              onLangChange('zh');
              setIsOpen(false);
            }}
            className={`w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-xs transition cursor-pointer ${
              currentLang === 'zh'
                ? 'theme-pill-active font-medium'
                : 'opacity-70 hover:opacity-100 hover:theme-nested'
            }`}
          >
            <span>🇨🇳 简体中文</span>
            {currentLang === 'zh' && <Check className="w-3 h-3" />}
          </button>

          <button
            type="button"
            onClick={() => {
              onLangChange('en');
              setIsOpen(false);
            }}
            className={`w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-xs transition cursor-pointer ${
              currentLang === 'en'
                ? 'theme-pill-active font-medium'
                : 'opacity-70 hover:opacity-100 hover:theme-nested'
            }`}
          >
            <span>🇺🇸 English</span>
            {currentLang === 'en' && <Check className="w-3 h-3" />}
          </button>
        </div>
      )}
    </div>
  );
};
