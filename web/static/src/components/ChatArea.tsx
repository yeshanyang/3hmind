import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Volume2, VolumeX, Sparkles, Terminal, Shield, Workflow, MessageSquare, Flame } from 'lucide-react';
import { Message } from '../types';

interface ChatAreaProps {
  messages: Message[];
  activeSpeakingId: string | null;
  onSpeakMessage: (id: string, text: string) => void;
  convState: 'idle' | 'listening' | 'processing' | 'speaking';
}

export default function ChatArea({
  messages,
  activeSpeakingId,
  onSpeakMessage,
  convState,
}: ChatAreaProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom when new items enter
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages, convState]);

  // Formatter for markdown-like text elements
  const formatText = (text: string) => {
    if (!text) return null;
    const lines = text.split('\n');

    return lines.map((line, idx) => {
      let trimmed = line.trim();

      // Check header matches
      if (trimmed.startsWith('###')) {
        return (
          <h4 key={idx} className="text-sm font-bold text-slate-100 mt-4 mb-2 tracking-wide font-sans border-l-2 border-blue-500 pl-2">
            {trimmed.replace(/^###\s*/, '')}
          </h4>
        );
      }
      if (trimmed.startsWith('##')) {
        return (
          <h3 key={idx} className="text-base font-bold text-blue-400 mt-5 mb-3 tracking-tight">
            {trimmed.replace(/^##\s*/, '')}
          </h3>
        );
      }
      if (trimmed.startsWith('#')) {
        return (
          <h2 key={idx} className="text-lg font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400 mt-6 mb-4">
            {trimmed.replace(/^#\s*/, '')}
          </h2>
        );
      }

      // Check bullets List
      if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
        const item = trimmed.replace(/^[-*]\s*/, '');
        // Highlight bold subparts
        const parts = item.split('—');
        if (parts.length > 1) {
          return (
            <li key={idx} className="text-xs text-white/80 leading-relaxed list-none pl-4 relative my-1.5 flex items-start gap-1">
              <span className="text-blue-400 mr-1.5">•</span>
              <span>
                <strong className="text-blue-300 font-medium">{parts[0]}</strong>—{parts.slice(1).join('—')}
              </span>
            </li>
          );
        }
        return (
          <li key={idx} className="text-xs text-white/80 leading-relaxed list-none pl-4 relative my-1.5 flex items-start gap-1">
            <span className="text-blue-400 mr-1.5">•</span>
            <span>{item}</span>
          </li>
        );
      }

      // Check divider lines or dashes
      if (/^[=\-*#\s]{5,}$/.test(trimmed)) {
        return <hr key={idx} className="my-4 border-white/10" />;
      }

      if (!trimmed) return <div key={idx} className="h-2" />;

      // Normal paragraph check and bold highlights
      const formattedLine = trimmed.split(/(\*\*.*?\*\*)/g).map((part, pIdx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={pIdx} className="text-blue-300 font-semibold">{part.slice(2, -2)}</strong>;
        }
        return part;
      });

      return <p key={idx} className="text-xs text-white/80 leading-relaxed my-1">{formattedLine}</p>;
    });
  };

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-6 py-6 space-y-5 bg-transparent scroll-smooth z-10"
    >
      {/* If empty, show beautiful high-end diagnostic dashboard info */}
      {messages.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="max-w-3xl mx-auto space-y-6 pt-4"
        >
          {/* Main Hero Card */}
          <div className="relative overflow-hidden rounded-3xl p-8 bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl">
            <div className="absolute top-0 right-0 w-[200px] h-[200px] rounded-full bg-blue-600/5 blur-3xl -z-10" />
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 shadow-md">
                <Sparkles className="w-5.5 h-5.5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white tracking-wide font-sans">3hmind 自我成长协同智能体</h2>
                <p className="text-xs text-white/50 font-mono font-medium">CONVERSATIONAL INTELLIGENCE PROTOCOL</p>
              </div>
            </div>
            <p className="text-xs text-white/85 leading-relaxed font-sans mb-5">
              欢迎启动 3hmind 神经网络工作栈。这是一个高度自主的成长教练系统，旨在通过连续对话和多维反馈支持您的职业技术和深层思维突破。
            </p>

            {/* Quick operations protocols list */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2 shadow-inner">
                <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Terminal className="w-4 h-4 text-blue-400" />
                  <span>流式连续对话协议</span>
                </h3>
                <ol className="text-xs text-white/70 space-y-1.5 pl-4 list-decimal leading-relaxed">
                  <li>点击右上角<strong>在线对话</strong>启动监听循环；</li>
                  <li>说完直接释放，系统进行语义整理、追问、播报；</li>
                  <li>AI 朗读完毕后自动重启拾音，形成闭环；</li>
                  <li>随时按<strong>停止</strong>来挂载或撤除当前任务。</li>
                </ol>
              </div>

              <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2 shadow-inner">
                <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Shield className="w-4 h-4 text-blue-400" />
                  <span>系统核心能力谱</span>
                </h3>
                <ul className="text-xs text-white/70 space-y-1.5 pl-4 list-none leading-relaxed">
                  <li className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> 独立 SQLite 与 Chroma 向量检索</li>
                  <li className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> 8大主题心智记忆自动归并</li>
                  <li className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> 引导性 4-6 递进式专家探寻</li>
                  <li className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> SSE 异步流式秒级响应输出</li>
                </ul>
              </div>
            </div>
          </div>
        </motion.div>
      ) : (
        <div className="max-w-3xl mx-auto space-y-5">
          <AnimatePresence initial={false}>
            {messages.map((msg) => {
              const isUser = msg.role === 'user';
              const isSystem = msg.role === 'system';

              if (isSystem) {
                return (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex justify-center"
                  >
                    <span className="px-3.5 py-1.5 rounded-md bg-white/5 backdrop-blur-md border border-white/10 text-[9px] font-mono text-white/40 tracking-widest text-center uppercase">
                      {msg.text}
                    </span>
                  </motion.div>
                );
              }

              return (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                  className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`relative max-w-[85%] rounded-2xl p-4.5 group transition-all text-sm leading-relaxed ${
                    isUser
                      ? 'bg-indigo-600/15 text-white border border-white/15 shadow-xl rounded-tr-sm backdrop-blur-md'
                      : 'bg-white/5 border border-white/10 shadow-md rounded-tl-sm backdrop-blur-md'
                  }`}>
                    {/* Message metadata details */}
                    <div className="flex items-center justify-between gap-4 mb-2 opacity-45 text-[9px] font-mono select-none">
                      <span className="flex items-center gap-1 font-bold">
                        {isUser ? (
                          <>
                            <Workflow className="w-3 h-3 text-blue-400 font-semibold" />
                            <span>COGNITIVE NODE (USER)</span>
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-3 h-3 text-blue-400 font-semibold" />
                            <span>COGNITIVE CORE (3HMIND)</span>
                          </>
                        )}
                      </span>
                      <span>
                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>

                    {/* Formatted body message content */}
                    <div className="space-y-1.5 pr-4 break-words text-white/90">
                      {formatText(msg.text)}
                    </div>

                    {/* Speech control icon button for longer agent replies */}
                    {!isUser && msg.text.length > 20 && (
                      <button
                        onClick={() => onSpeakMessage(msg.id, msg.text)}
                        className={`absolute bottom-3 right-3 text-white/40 hover:text-white bg-white/5 p-1.5 rounded-lg border border-white/10 transition-all text-xs cursor-pointer ${
                          activeSpeakingId === msg.id
                            ? 'text-blue-400 bg-blue-500/15 border-blue-500/25 flex shadow-lg'
                            : 'hidden group-hover:flex'
                        }`}
                        title={activeSpeakingId === msg.id ? '正在朗读 — 点击静音' : '朗读此条回复'}
                      >
                        {activeSpeakingId === msg.id ? (
                          <VolumeX className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
                        ) : (
                          <Volume2 className="w-3.5 h-3.5" />
                        )}
                      </button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>

          {/* Typing Loading Indicator */}
          {convState === 'processing' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex justify-start"
            >
              <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl rounded-tl-sm p-4.5 flex items-center gap-2">
                <Flame className="w-4 h-4 text-blue-400 animate-spin" />
                <span className="text-xs text-white/50 font-mono tracking-widest uppercase animate-pulse">
                  智能体正在深度思考并加载记忆流
                </span>
                <span className="flex gap-1 pl-1">
                  <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
                  <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
                  <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" />
                </span>
              </div>
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
}
