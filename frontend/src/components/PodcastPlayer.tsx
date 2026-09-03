import React, { useState, useRef, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  RotateCw, 
  Download, 
  Volume2, 
  VolumeX, 
  Sparkles, 
  Radio, 
  Mic2, 
  Headphones, 
  Loader2, 
  ChevronDown, 
  ChevronUp,
  X,
  FileText
} from 'lucide-react';
import { generatePodcast, fetchPodcastMetadata, PodcastData, PodcastTurn } from '../lib/api';

interface PodcastPlayerProps {
  taskId: string;
  title: string;
  isOpen: boolean;
  onClose: () => void;
}

export const PodcastPlayer: React.FC<PodcastPlayerProps> = ({
  taskId,
  title,
  isOpen,
  onClose
}) => {
  const [loading, setLoading] = useState(false);
  const [podcastData, setPodcastData] = useState<PodcastData | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [isMuted, setIsMuted] = useState(false);
  const [activeTurnIndex, setActiveTurnIndex] = useState(0);
  const [showTranscript, setShowTranscript] = useState(true);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  // 打开弹窗时尝试获取已有播客，若无则自动触发生成
  useEffect(() => {
    if (!isOpen || !taskId) return;
    let isMounted = true;

    fetchPodcastMetadata(taskId)
      .then((data) => {
        if (isMounted && data && data.script) {
          setPodcastData(data);
        }
      })
      .catch(() => {
        // 未生成则自动触发一次生成
        handleGenerate();
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, taskId]);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      let customLLMCfg = null;
      try {
        const saved = localStorage.getItem('deep_research_custom_llm');
        if (saved) customLLMCfg = JSON.parse(saved);
      } catch {}

      const data = await generatePodcast(taskId, customLLMCfg);
      setPodcastData(data);
    } catch (e) {
      console.error('生成播客失败:', e);
    } finally {
      setLoading(false);
    }
  };

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().catch(console.error);
      setIsPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (!audioRef.current) return;
    const cur = audioRef.current.currentTime;
    setCurrentTime(cur);

    // 根据播放时间估算当前朗读的台词段落
    if (podcastData && podcastData.script && duration > 0) {
      const turns = podcastData.script;
      const totalChars = turns.reduce((acc, t) => acc + t.text.length, 0);
      let cumulativeChars = 0;
      for (let i = 0; i < turns.length; i++) {
        cumulativeChars += turns[i].text.length;
        if (cur <= (cumulativeChars / totalChars) * duration) {
          setActiveTurnIndex(i);
          break;
        }
      }
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = val;
      setCurrentTime(val);
    }
  };

  const skipTime = (seconds: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.max(0, Math.min(duration, audioRef.current.currentTime + seconds));
    }
  };

  const cycleSpeed = () => {
    const rates = [1.0, 1.25, 1.5, 0.75];
    const nextIdx = (rates.indexOf(playbackRate) + 1) % rates.length;
    const nextRate = rates[nextIdx];
    setPlaybackRate(nextRate);
    if (audioRef.current) {
      audioRef.current.playbackRate = nextRate;
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  if (!isOpen) return null;

  const currentSpeaker = podcastData?.script?.[activeTurnIndex]?.speaker || 'Yunxi';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-3xl bg-slate-900 border border-slate-700/80 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh] text-white"
        onClick={e => e.stopPropagation()}
      >
        {/* 顶部标题栏 */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <Headphones className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-100">
                  NotebookLM 级双角色对谈播客
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-purple-400" />
                  AI Deep Dive
                </span>
              </div>
              <p className="text-xs text-slate-400 truncate max-w-md mt-0.5">{title}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 主体交互区 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 space-y-4 text-center animate-in fade-in">
              <div className="w-16 h-16 rounded-3xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center shadow-xl shadow-purple-500/10 animate-pulse">
                <Radio className="w-8 h-8 text-purple-400 animate-spin" />
              </div>
              <div className="space-y-1">
                <div className="text-sm font-bold text-slate-100 flex items-center justify-center gap-2">
                  <span>AI 编剧正在构思双人对谈剧本...</span>
                </div>
                <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
                  正在由大模型将万字报告改编为「云希」与「晓晓」生动对话，并调用微软神经网络双音色分段合成。
                </p>
              </div>
            </div>
          ) : !podcastData ? (
            <div className="text-center py-16 space-y-4">
              <p className="text-sm text-slate-400">尚未生成本期对谈播客</p>
              <button
                onClick={handleGenerate}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 text-white text-xs font-bold shadow-lg shadow-purple-500/20 cursor-pointer"
              >
                立即生成双人深度播客
              </button>
            </div>
          ) : (
            <>
              {/* 双主持人互动舞台 */}
              <div className="grid grid-cols-2 gap-4">
                {/* 云希 (Host A) */}
                <div className={`p-4 rounded-2xl border transition-all duration-300 flex items-center gap-3.5 ${
                  currentSpeaker === 'Yunxi' && isPlaying 
                    ? 'bg-blue-950/40 border-cyan-400/60 shadow-lg shadow-cyan-500/10 ring-2 ring-cyan-500/20' 
                    : 'bg-slate-800/40 border-slate-700/60 opacity-75'
                }`}>
                  <div className="relative">
                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-xl shadow-md">
                      👨‍💼
                    </div>
                    {currentSpeaker === 'Yunxi' && isPlaying && (
                      <span className="absolute -top-1 -right-1 flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500"></span>
                      </span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-bold text-slate-100">云希</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-cyan-500/20 text-cyan-300 font-medium">行业观察员</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                      {currentSpeaker === 'Yunxi' && isPlaying ? '🎙️ 正在发言中...' : '专注商业矛盾与通俗比喻'}
                    </p>
                  </div>
                </div>

                {/* 晓晓 (Host B) */}
                <div className={`p-4 rounded-2xl border transition-all duration-300 flex items-center gap-3.5 ${
                  currentSpeaker === 'Xiaoxiao' && isPlaying 
                    ? 'bg-purple-950/40 border-purple-400/60 shadow-lg shadow-purple-500/10 ring-2 ring-purple-500/20' 
                    : 'bg-slate-800/40 border-slate-700/60 opacity-75'
                }`}>
                  <div className="relative">
                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center text-xl shadow-md">
                      👩‍🔬
                    </div>
                    {currentSpeaker === 'Xiaoxiao' && isPlaying && (
                      <span className="absolute -top-1 -right-1 flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-purple-500"></span>
                      </span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-bold text-slate-100">晓晓</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-purple-500/20 text-purple-300 font-medium">前沿技术专家</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                      {currentSpeaker === 'Xiaoxiao' && isPlaying ? '🎙️ 正在剖析底层原理...' : '专注物理机理与量化预测'}
                    </p>
                  </div>
                </div>
              </div>

              {/* 核心播放器控制条 */}
              <div className="p-5 rounded-2xl bg-slate-950/80 border border-slate-800/90 space-y-3.5">
                {/* 隐藏的 HTML5 Audio */}
                <audio
                  ref={audioRef}
                  src={podcastData.audio_url}
                  onTimeUpdate={handleTimeUpdate}
                  onLoadedMetadata={handleLoadedMetadata}
                  onEnded={() => setIsPlaying(false)}
                />

                {/* 进度条与时间 */}
                <div className="space-y-1">
                  <input
                    type="range"
                    min={0}
                    max={duration || 100}
                    value={currentTime}
                    onChange={handleSeek}
                    className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                  />
                  <div className="flex justify-between text-[11px] font-mono text-slate-400">
                    <span>{formatTime(currentTime)}</span>
                    <span>{formatTime(duration)}</span>
                  </div>
                </div>

                {/* 按钮控制组 */}
                <div className="flex items-center justify-between pt-1">
                  {/* 倍速切换 */}
                  <button
                    onClick={cycleSpeed}
                    className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs font-semibold transition cursor-pointer"
                  >
                    {playbackRate}x
                  </button>

                  {/* 中间主要播放按键 */}
                  <div className="flex items-center gap-4">
                    <button
                      onClick={() => skipTime(-10)}
                      className="p-2 text-slate-400 hover:text-white transition cursor-pointer"
                      title="后退 10 秒"
                    >
                      <RotateCcw className="w-5 h-5" />
                    </button>

                    <button
                      onClick={togglePlay}
                      className="w-12 h-12 rounded-full bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500 flex items-center justify-center text-white shadow-lg shadow-cyan-500/25 transition cursor-pointer"
                    >
                      {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 ml-0.5" />}
                    </button>

                    <button
                      onClick={() => skipTime(10)}
                      className="p-2 text-slate-400 hover:text-white transition cursor-pointer"
                      title="前进 10 秒"
                    >
                      <RotateCw className="w-5 h-5" />
                    </button>
                  </div>

                  {/* 右侧动作 */}
                  <div className="flex items-center gap-2">
                    <a
                      href={podcastData.audio_url}
                      download={`${title}_双人播客.mp3`}
                      className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition cursor-pointer"
                      title="下载完整播客 MP3"
                    >
                      <Download className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              </div>

              {/* 台词剧本文稿抽屉 */}
              <div className="space-y-2">
                <button
                  onClick={() => setShowTranscript(!showTranscript)}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition cursor-pointer"
                >
                  <span className="flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-purple-400" />
                    双人对谈实时交互剧本 ({podcastData.script.length} 轮互动)
                  </span>
                  {showTranscript ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {showTranscript && (
                  <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1">
                    {podcastData.script.map((turn, i) => {
                      const isActive = i === activeTurnIndex;
                      const isYunxi = turn.speaker === 'Yunxi';
                      return (
                        <div
                          key={i}
                          className={`p-3 rounded-xl border transition-all text-xs leading-relaxed ${
                            isActive
                              ? isYunxi 
                                ? 'bg-cyan-950/40 border-cyan-500/50 text-slate-100 shadow-sm'
                                : 'bg-purple-950/40 border-purple-500/50 text-slate-100 shadow-sm'
                              : 'bg-slate-900/40 border-slate-800/80 text-slate-400 hover:bg-slate-900/80'
                          }`}
                        >
                          <div className="flex items-center justify-between font-bold mb-1">
                            <span className={isYunxi ? 'text-cyan-400' : 'text-purple-400'}>
                              {turn.name} ({turn.role})
                            </span>
                            {isActive && (
                              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/10 text-white">
                                正在朗读
                              </span>
                            )}
                          </div>
                          <p>{turn.text}</p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* 底部动作条 */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/90 flex items-center justify-between text-xs text-slate-400">
          <span>基于微软神经网络语音与大语言模型双重调度</span>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span>重新编排播客</span>
          </button>
        </div>
      </div>
    </div>
  );
};
