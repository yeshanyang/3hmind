import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Plus, Send, Radio } from 'lucide-react';
import { ConvState } from '../types';

interface ChatInputProps {
  onSendText: (text: string) => void;
  onToggleMic: () => void;
  onOpenMediaModal: () => void;
  convState: ConvState;
  voicePaused: boolean;
  convMode: boolean;
  voiceTranscript: string;
}

export default function ChatInput({
  onSendText,
  onToggleMic,
  onOpenMediaModal,
  convState,
  voicePaused,
  convMode,
  voiceTranscript,
}: ChatInputProps) {
  const [inputText, setInputText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const isListening = convState === 'listening';
  const isProcessing = convState === 'processing';

  const handleSend = () => {
    if (!inputText.trim()) return;
    onSendText(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  // Keep input focused if needed
  useEffect(() => {
    if (convState === 'idle' && inputRef.current) {
      inputRef.current.focus();
    }
  }, [convState]);

  return (
    <div className="p-4 bg-white/5 backdrop-blur-xl border-t border-white/10 flex flex-col gap-3 relative shadow-[0_-8px_32px_rgba(0,0,0,0.1)] select-none z-20">
      {/* Visual soundwave spectrum overlay while in listening state */}
      {isListening && (
        <div className="absolute top-[-2px] left-0 right-0 h-[2px] bg-blue-500/20 overflow-hidden flex justify-around">
          <div className="w-[8%] h-full bg-gradient-to-r from-transparent via-blue-400 to-transparent animate-pulse [animation-duration:0.6s]" />
          <div className="w-[12%] h-full bg-gradient-to-r from-transparent via-indigo-500 to-transparent animate-pulse [animation-duration:0.9s]" />
          <div className="w-[15%] h-full bg-gradient-to-r from-transparent via-blue-400 to-transparent animate-pulse [animation-duration:0.4s]" />
          <div className="w-[20%] h-full bg-gradient-to-r from-transparent via-indigo-400 to-transparent animate-pulse [animation-duration:1.1s]" />
        </div>
      )}

      <div className="max-w-4xl mx-auto w-full flex items-center gap-3">
        {/* Glowing microphone trigger core */}
        <div className="relative group">
          <button
            onClick={onToggleMic}
            className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 relative border cursor-pointer ${
              isListening
                ? 'bg-rose-600 text-white border-rose-500 shadow-[0_0_20px_rgba(239,68,68,0.4)] animate-pulse'
                : voicePaused
                ? 'bg-amber-600/20 text-amber-400 border-amber-500/40 shadow-[0_0_12px_rgba(245,158,11,0.25)] animate-pulse'
                : convMode
                ? 'bg-blue-600/10 text-blue-400 border-blue-500/30 hover:bg-blue-600/20'
                : 'bg-white/5 text-white/85 border-white/10 hover:bg-white/10 hover:text-white'
            }`}
            title={isListening ? '点击关闭声源监听' : '启动麦克风语音录入/连续流式对话'}
          >
            {isListening ? (
              <Radio className="w-5 h-5 animate-spin" />
            ) : (
              <Mic className="w-5 h-5" />
            )}
            {/* Visual indicator crown */}
            {isListening && <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-rose-500 border border-white rounded-full animate-ping" />}
          </button>
        </div>

        {/* Text Area field */}
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={isListening && voiceTranscript ? voiceTranscript : inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isListening
                ? "系统正在聆听... （说出“说完了”/“就这样”可快捷发送，点击录音按钮停止）"
                : voicePaused
                ? "语音已暂停。手动打字中... （5秒无动作后将自动切回连续声音识别）"
                : "输入您想要分析的想法或成长问题..."
            }
            className={`w-full pl-4 pr-12 py-3.5 text-sm rounded-xl outline-none glass-input text-white placeholder:text-white/20 transition-all ${
              isListening ? 'border-blue-500/45 shadow-[0_0_12px_rgba(59,130,246,0.15)]' : ''
            }`}
          />
          {/* Multimodality button inline inside input */}
          <button
            onClick={onOpenMediaModal}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1.5 rounded-lg bg-black/20 text-white/40 hover:text-blue-400 border border-transparent hover:border-white/10 active:scale-90 transition-all cursor-pointer"
            title="上传分析外部文档、音频、视频或载入视频流 (Multimodal Inputs)"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* Dispatch text message button */}
        <button
          onClick={handleSend}
          disabled={!inputText.trim() || isProcessing}
          className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 hover:from-indigo-600 hover:to-blue-700 disabled:opacity-30 flex items-center justify-center text-white border border-white/10 shadow-lg hover:shadow-blue-500/10 duration-200 active:scale-95 cursor-pointer"
          title="发送文字并加入思维模型队列"
        >
          <Send className="w-4.5 h-4.5" />
        </button>
      </div>
    </div>
  );
}
