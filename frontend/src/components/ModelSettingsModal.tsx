import React, { useState, useEffect } from 'react';
import { 
  X, 
  Cpu, 
  Key, 
  Globe, 
  Zap, 
  Eye, 
  EyeOff, 
  Check, 
  AlertCircle, 
  RotateCcw, 
  Loader2 
} from 'lucide-react';
import { CustomLLMConfig, TestConnectionResponse } from '../types';
import { testCustomModelConnection } from '../lib/api';
import { Language, translations } from '../locales/translations';

interface ModelSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentLang?: Language;
  onConfigSaved?: (config: CustomLLMConfig | null) => void;
}

export const LOCAL_STORAGE_KEY = 'dra_custom_llm_config';

export function getStoredCustomLLMConfig(): CustomLLMConfig | null {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export const ModelSettingsModal: React.FC<ModelSettingsModalProps> = ({
  isOpen,
  onClose,
  currentLang = 'zh',
  onConfigSaved
}) => {
  const t = translations[currentLang].customLLM;

  const [provider, setProvider] = useState<'openai' | 'anthropic'>('openai');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [modelName, setModelName] = useState('');
  const [temperature, setTemperature] = useState<number>(0.3);
  const [showApiKey, setShowApiKey] = useState(false);

  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestConnectionResponse | null>(null);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState(false);

  // 初始化加载 localStorage
  useEffect(() => {
    if (isOpen) {
      const stored = getStoredCustomLLMConfig();
      if (stored) {
        setProvider(stored.provider_type || 'openai');
        setBaseUrl(stored.base_url || '');
        setApiKey(stored.api_key || '');
        setModelName(stored.model_name || '');
        setTemperature(stored.temperature ?? 0.3);
      } else {
        setProvider('openai');
        setBaseUrl('');
        setApiKey('');
        setModelName('');
        setTemperature(0.3);
      }
      setTestResult(null);
      setSaveSuccessMsg(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const currentConfig: CustomLLMConfig = {
    provider_type: provider,
    base_url: baseUrl.trim() || undefined,
    api_key: apiKey.trim() || undefined,
    model_name: modelName.trim() || undefined,
    temperature: temperature
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await testCustomModelConnection(currentConfig);
      setTestResult(res);
    } catch (e: any) {
      setTestResult({ success: false, error: e.message || '网络连接异常' });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = () => {
    const hasValue = baseUrl.trim() || apiKey.trim() || modelName.trim();
    if (hasValue) {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(currentConfig));
      if (onConfigSaved) onConfigSaved(currentConfig);
    } else {
      localStorage.removeItem(LOCAL_STORAGE_KEY);
      if (onConfigSaved) onConfigSaved(null);
    }
    setSaveSuccessMsg(true);
    setTimeout(() => {
      setSaveSuccessMsg(false);
      onClose();
    }, 1200);
  };

  const handleReset = () => {
    localStorage.removeItem(LOCAL_STORAGE_KEY);
    setProvider('openai');
    setBaseUrl('');
    setApiKey('');
    setModelName('');
    setTemperature(0.3);
    setTestResult(null);
    if (onConfigSaved) onConfigSaved(null);
    setSaveSuccessMsg(true);
    setTimeout(() => {
      setSaveSuccessMsg(false);
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-xl theme-card border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Modal 头部 */}
        <div className="p-5 border-b flex items-center justify-between theme-nested">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-500">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold">{t.title}</h3>
              <p className="text-xs opacity-60 line-clamp-1">{t.subtitle}</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg opacity-60 hover:opacity-100 theme-nested hover:bg-black/10 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal 主表单 */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1 font-sans text-xs">
          
          {/* 协议类型切换 */}
          <div>
            <label className="block font-medium mb-1.5 opacity-80">{t.providerLabel}</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setProvider('openai')}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  provider === 'openai' 
                    ? 'border-blue-500 bg-blue-500/10 text-blue-600 dark:text-blue-400 font-semibold' 
                    : 'border-white/10 opacity-70 hover:opacity-100'
                }`}
              >
                <div className="font-bold text-xs">OpenAI 兼容协议</div>
                <div className="text-[11px] opacity-70 mt-0.5">DeepSeek, Qwen, Ollama, OneAPI</div>
              </button>
              <button
                type="button"
                onClick={() => setProvider('anthropic')}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  provider === 'anthropic' 
                    ? 'border-blue-500 bg-blue-500/10 text-blue-600 dark:text-blue-400 font-semibold' 
                    : 'border-white/10 opacity-70 hover:opacity-100'
                }`}
              >
                <div className="font-bold text-xs">Anthropic 原生协议</div>
                <div className="text-[11px] opacity-70 mt-0.5">Claude 3.5 Sonnet (/v1/messages)</div>
              </button>
            </div>
          </div>

          {/* Base URL */}
          <div>
            <label className="block font-medium mb-1.5 opacity-80 flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5" />
              <span>{t.baseUrlLabel}</span>
            </label>
            <input 
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={provider === 'anthropic' ? 'https://api.anthropic.com' : t.baseUrlPlaceholder}
              className="w-full px-3 py-2 rounded-xl theme-input border border-white/10 focus:outline-none focus:border-blue-500 transition-all"
            />
          </div>

          {/* API Key */}
          <div>
            <label className="block font-medium mb-1.5 opacity-80 flex items-center gap-1.5">
              <Key className="w-3.5 h-3.5" />
              <span>{t.apiKeyLabel}</span>
            </label>
            <div className="relative">
              <input 
                type={showApiKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={t.apiKeyPlaceholder}
                className="w-full px-3 py-2 pr-10 rounded-xl theme-input border border-white/10 focus:outline-none focus:border-blue-500 font-mono transition-all"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 opacity-50 hover:opacity-100"
              >
                {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* 模型名称 */}
          <div>
            <label className="block font-medium mb-1.5 opacity-80 flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5" />
              <span>{t.modelNameLabel}</span>
            </label>
            <input 
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder={provider === 'anthropic' ? 'claude-3-5-sonnet-20241022' : t.modelNamePlaceholder}
              className="w-full px-3 py-2 rounded-xl theme-input border border-white/10 focus:outline-none focus:border-blue-500 font-mono transition-all"
            />
          </div>

          {/* 采样温度 */}
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="font-medium opacity-80">{t.tempLabel}</label>
              <span className="font-mono font-semibold text-blue-500">{temperature.toFixed(2)}</span>
            </div>
            <input 
              type="range" 
              min="0.0" 
              max="1.0" 
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full accent-blue-500 cursor-pointer"
            />
          </div>

          {/* 测试连接反馈区域 */}
          {testResult && (
            <div className={`p-3 rounded-xl border flex items-start gap-2.5 transition-all ${
              testResult.success 
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500' 
                : 'bg-rose-500/10 border-rose-500/30 text-rose-500'
            }`}>
              {testResult.success ? <Check className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />}
              <div className="text-xs">
                <div className="font-bold">
                  {testResult.success 
                    ? t.testSuccess.replace('{ms}', String(testResult.latency_ms ?? 0))
                    : t.testFail.replace('{err}', testResult.error || '未知错误')}
                </div>
                {testResult.reply && (
                  <div className="text-[11px] opacity-80 mt-1 font-mono">回包: "{testResult.reply}"</div>
                )}
              </div>
            </div>
          )}

          {saveSuccessMsg && (
            <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-500 flex items-center gap-2 text-xs font-semibold">
              <Check className="w-4 h-4" />
              <span>{t.savedMsg}</span>
            </div>
          )}

        </div>

        {/* Modal 底部按钮 */}
        <div className="p-4 border-t theme-nested flex items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={isTesting}
              onClick={handleTestConnection}
              className="px-3.5 py-2 rounded-xl border border-blue-500/30 text-blue-500 hover:bg-blue-500/10 transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
            >
              {isTesting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
              <span>{isTesting ? t.testingBtn : t.testBtn}</span>
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="px-3 py-2 rounded-xl opacity-60 hover:opacity-100 hover:bg-black/10 transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>{t.resetBtn}</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-xl border border-white/10 opacity-70 hover:opacity-100 transition-all cursor-pointer"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium shadow-md transition-all cursor-pointer"
            >
              {t.saveBtn}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
