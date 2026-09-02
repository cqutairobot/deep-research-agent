import React, { useState, useRef, useEffect } from 'react';
import { Palette, Check } from 'lucide-react';
import { Language, translations } from '../locales/translations';

export type ThemeType = 'dark' | 'vintage' | 'light' | 'emerald';

interface ThemeSelectorProps {
  currentTheme: ThemeType;
  onThemeChange: (theme: ThemeType) => void;
  currentLang?: Language;
}

export const ThemeSelector: React.FC<ThemeSelectorProps> = ({
  currentTheme,
  onThemeChange,
  currentLang = 'zh'
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const t = translations[currentLang];

  const themes: { id: ThemeType; name: string; desc: string; colors: string[] }[] = [
    {
      id: 'vintage',
      name: t.themes.vintage,
      desc: currentLang === 'zh' ? '宋代宣纸 · 徽墨文雅 · 朱砂红' : 'Song Dynasty Parchment & Cinnabar',
      colors: ['#f4ecd8', '#2a1d0f', '#b91c1c']
    },
    {
      id: 'light',
      name: t.themes.light,
      desc: currentLang === 'zh' ? '纯净雪白 · 极简雅致 · 皇家蓝' : 'Pure Crisp White & Royal Blue',
      colors: ['#f8fafc', '#0f172a', '#2563eb']
    },
    {
      id: 'emerald',
      name: t.themes.emerald,
      desc: currentLang === 'zh' ? '苍翠松林 · 薄荷青绿 · 北欧极光' : 'Nordic Emerald & Aurora Forest',
      colors: ['#061712', '#a7f3d0', '#059669']
    },
    {
      id: 'dark',
      name: t.themes.dark,
      desc: currentLang === 'zh' ? '极客深蓝 · 霓虹电光 · 赛博空间' : 'Cyber Electric Blue & Deep Space',
      colors: ['#080c14', '#f8fafc', '#3b82f6']
    }
  ];

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
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg theme-card text-xs opacity-90 hover:opacity-100 transition shadow-sm cursor-pointer"
        title="切换主题配色 / Switch Theme"
      >
        <Palette className="w-3.5 h-3.5 theme-accent-text" />
        <span className="hidden sm:inline font-medium">
          {themes.find(t => t.id === currentTheme)?.name || '主题'}
        </span>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 theme-surface rounded-2xl p-2 shadow-2xl border border-subtle z-50 animate-in fade-in zoom-in-95 duration-150 space-y-1">
          <div className="text-[10px] opacity-60 px-2 py-1 font-mono uppercase tracking-wider">
            {t.nav.theme}
          </div>
          {themes.map((theme) => {
            const isSelected = currentTheme === theme.id;
            return (
              <button
                key={theme.id}
                type="button"
                onClick={() => {
                  onThemeChange(theme.id);
                  setIsOpen(false);
                }}
                className={`w-full flex items-center justify-between p-2 rounded-xl text-left transition cursor-pointer ${
                  isSelected
                    ? 'theme-pill-active font-semibold shadow-md'
                    : 'hover:theme-nested opacity-80 hover:opacity-100'
                }`}
              >
                <div className="space-y-0.5">
                  <div className="text-xs font-bold">{theme.name}</div>
                  <div className="text-[10px] opacity-75">{theme.desc}</div>
                </div>

                <div className="flex items-center gap-1.5">
                  <div className="flex -space-x-1">
                    {theme.colors.map((c, i) => (
                      <span
                        key={i}
                        className="w-2.5 h-2.5 rounded-full border border-black/20"
                        style={{ backgroundColor: c }}
                      />
                    ))}
                  </div>
                  {isSelected && <Check className="w-3.5 h-3.5 text-white" />}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
