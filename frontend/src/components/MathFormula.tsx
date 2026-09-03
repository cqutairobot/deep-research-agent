import React, { useMemo } from 'react';
import katex from 'katex';

interface MathFormulaProps {
  formula: string;
  displayMode?: boolean;
}

export const MathFormula: React.FC<MathFormulaProps> = ({ formula, displayMode = false }) => {
  const html = useMemo(() => {
    try {
      const cleanFormula = formula
        .replace(/^\\\[\s*/, '')
        .replace(/\s*\\\]$/, '')
        .replace(/^\$\$\s*/, '')
        .replace(/\s*\$\$$/, '')
        .replace(/^\\\(\s*/, '')
        .replace(/\s*\\\)$/, '')
        .replace(/^\$\s*/, '')
        .replace(/\s*\$$/, '')
        .trim();

      return katex.renderToString(cleanFormula, {
        displayMode,
        throwOnError: false,
        strict: false
      });
    } catch (e: any) {
      return `<span class="text-red-500 font-mono text-xs">${formula}</span>`;
    }
  }, [formula, displayMode]);

  if (displayMode) {
    return (
      <div 
        className="my-4 py-3.5 px-4 overflow-x-auto flex items-center justify-center theme-nested rounded-2xl border border-subtle shadow-xs text-sm"
        dangerouslySetInnerHTML={{ __html: html }} 
      />
    );
  }

  return (
    <span 
      className="inline-block px-1 align-baseline"
      dangerouslySetInnerHTML={{ __html: html }} 
    />
  );
};
