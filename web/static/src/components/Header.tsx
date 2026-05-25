import { Volume2, VolumeX, HeartHandshake, Mic, Power, Terminal, Radio } from 'lucide-react';
import { ConvState } from '../types';

interface HeaderProps {
  currentUser: string;
  autoSpeak: boolean;
  onToggleAutoSpeak: () => void;
  autoAsk: boolean;
  onToggleAutoAsk: () => void;
  convMode: boolean;
  onToggleConvMode: () => void;
  convState: ConvState;
  onStopAll: () => void;
  onLogout: () => void;
  inquiryActive: boolean;
}

export default function Header({
  currentUser,
  autoSpeak,
  onToggleAutoSpeak,
  autoAsk,
  onToggleAutoAsk,
  convMode,
  onToggleConvMode,
  convState,
  onStopAll,
  onLogout,
  inquiryActive,
}: HeaderProps) {

  // State colors mapping
  const stateColorMap = {
    idle: { bg: 'bg-emerald-500', shadow: 'shadow-emerald-500/50', label: '就绪' },
    listening: { bg: 'bg-rose-500 animate-pulse', shadow: 'shadow-rose-500/50', label: '聆听中' },
    processing: { bg: 'bg-amber-500 animate-pulse', shadow: 'shadow-amber-500/50', label: '思考中' },
    speaking: { bg: 'bg-teal-400 animate-pulse', shadow: 'shadow-teal-400/50', label: '播报中' }
  };

  const activeState = stateColorMap[convState] || stateColorMap.idle;

  return (
    <header className="px-8 py-4 bg-white/5 backdrop-blur-md border-b border-white/10 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 select-none z-10 shadow-[0_4px_30px_rgba(0,0,0,0.15)]">
      {/* Brand title */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-400 to-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-500/20">
            <span className="text-xs font-black font-sans text-white">3H</span>
          </div>
          {/* Accent dot overlay */}
          <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-[#0a0a14] flex items-center justify-center">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
          </div>
        </div>
        <div>
          <h1 className="text-lg font-bold text-white tracking-tight flex items-center gap-1.5">
            3hamind <span className="text-white/40 text-[10px] font-mono font-normal">v3.1</span>
          </h1>
          <p className="text-[9px] text-white/50 font-mono tracking-widest uppercase">自我成长协同智能体</p>
        </div>
      </div>

      {/* Control cluster */}
      <div className="flex flex-wrap items-center gap-3 bg-white/5 p-1.5 rounded-full border border-white/10 self-end md:self-auto backdrop-blur-xl">
        {/* Toggle Speech: Auto Speak */}
        <button
          onClick={onToggleAutoSpeak}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wide transition-all duration-200 cursor-pointer ${
            autoSpeak
              ? 'bg-blue-500/15 text-blue-400 border border-blue-500/25 shadow-[0_0_12px_rgba(59,130,246,0.15)]'
              : 'text-white/40 hover:text-white/80 border border-transparent'
          }`}
          title="语音播放 - 自动朗读AI回复"
        >
          {autoSpeak ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          <span>语音播报</span>
        </button>

        {/* Toggle Proactive Inquiry: Auto Ask */}
        <button
          onClick={onToggleAutoAsk}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wide transition-all duration-200 cursor-pointer ${
            autoAsk
              ? 'bg-purple-500/15 text-purple-400 border border-purple-500/25 shadow-[0_0_12px_rgba(168,85,247,0.15)]'
              : 'text-white/40 hover:text-white/80 border border-transparent'
          }`}
          title="AI主动追问 - 启发式深度探索引导"
        >
          <HeartHandshake className="w-4 h-4" />
          <span>AI追问</span>
        </button>

        {/* Toggle Real-time Dialog Mode: Continuous Audio */}
        <button
          onClick={onToggleConvMode}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wide transition-all duration-200 cursor-pointer ${
            convMode
              ? 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/25 shadow-[0_0_12px_rgba(99,102,241,0.15)]'
              : 'text-white/40 hover:text-white/80 border border-transparent'
          }`}
          title="流式连续拾音与播放交互环"
        >
          <Mic className="w-4 h-4 animate-pulse" />
          <span>在线对话</span>
        </button>

        {/* Dynamic Global Kill/Stop Switch */}
        {(convState !== 'idle' || inquiryActive) && (
          <button
            onClick={onStopAll}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold bg-rose-500/15 text-rose-400 border border-rose-500/25 shadow-[0_0_12px_rgba(244,63,94,0.15)] animate-pulse hover:bg-rose-500/30 transition-all duration-150 cursor-pointer"
            title="紧急中断所有正在进行的流处理、追问或播报任务"
          >
            <Radio className="w-4 h-4" />
            <span>停止所有</span>
          </button>
        )}

        {/* Telemetry connection status */}
        <div className="flex items-center gap-2 px-3 py-1.5 border border-white/10 rounded-full bg-white/5 font-mono text-[9px] tracking-widest uppercase">
          <div className="relative flex h-2 w-2">
            <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${activeState.bg}`} />
            <span className={`relative inline-flex rounded-full h-2 w-2 ${activeState.bg.split(' ')[0]}`} />
          </div>
          <span className="text-white/50">{activeState.label}</span>
        </div>
      </div>

      {/* User profile controls */}
      <div className="flex items-center gap-3 bg-white/5 border border-white/10 p-1 px-4 rounded-full backdrop-blur-xl">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500/10 to-indigo-600/10 border border-white/20 flex items-center justify-center text-[10px] font-bold font-mono text-blue-400">
            {currentUser.slice(0, 2).toUpperCase()}
          </div>
          <span className="text-xs font-medium text-white/80 font-sans tracking-wide">{currentUser}</span>
        </div>
        <div className="w-[1px] h-3.5 bg-white/10" />
        <button
          onClick={onLogout}
          className="text-white/40 hover:text-rose-400 active:scale-95 transition-all text-xs flex items-center gap-1 cursor-pointer font-medium"
          title="退出控制台并锁定凭证位"
        >
          <Power className="w-4 h-4" />
          <span className="hidden sm:inline">登出</span>
        </button>
      </div>
    </header>
  );
}
