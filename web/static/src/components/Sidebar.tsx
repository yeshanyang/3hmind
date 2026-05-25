import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Compass, Award, Activity, BrainCircuit, Waves, Hammer,
  FileText, Mic, Video, Camera, Plus, Trash2, Milestone,
  ChevronLeft, ChevronRight, Sparkles, Database, HelpCircle,
  TrendingUp, UserCheck, Play, Square, MessageSquareText
} from 'lucide-react';
import { Goal, Profile, InquiryQuestion } from '../types';

interface SidebarProps {
  apiCall: (path: string, options?: RequestInit) => Promise<Response>;
  profile: Profile;
  onRefreshProfile: () => void;
  onSendAction: (url: string) => void;
  onSendPlan: () => void;
  onLoadDashboard: () => void;
  onOpenMediaModal: (tab: string) => void;
  onAskProfileQuestion: () => void;
  // Deep Dialog / Inquiry
  inquiryActive: boolean;
  inquiryQuestions: InquiryQuestion[];
  inquiryIndex: number;
  inquiryTopic: string;
  waitingForInquiryAnswer: boolean;
  onStartInquiry: (topic: string) => void;
  onStopInquiry: () => void;
  inquiryInsightsCount: number;
  // Goals & Abilities
  goals: Goal[];
  onLoadGoals: () => void;
  onDeleteGoal: (id: number) => void;
  onAdvanceGoal: (id: number, currentPct: number) => void;
  onAssessGoal: (id: number) => void;
  // Sizing
  sidebarWidth: number;
  setSidebarWidth: (width: number) => void;
}

export default function Sidebar({
  apiCall,
  profile,
  onRefreshProfile,
  onSendAction,
  onSendPlan,
  onLoadDashboard,
  onOpenMediaModal,
  onAskProfileQuestion,
  inquiryActive,
  inquiryQuestions,
  inquiryIndex,
  inquiryTopic,
  onStartInquiry,
  onStopInquiry,
  inquiryInsightsCount,
  goals,
  onDeleteGoal,
  onAdvanceGoal,
  onAssessGoal,
  sidebarWidth,
  setSidebarWidth,
}: SidebarProps) {
  // Sidebar UI folding
  const [collapsed, setCollapsed] = useState(false);
  const [inquiryTopicInput, setInquiryTopicInput] = useState('');
  const [goalInput, setGoalInput] = useState('');
  const [abilityInput, setAbilityInput] = useState('');

  // Local state copy of profile inputs
  const [role, setRole] = useState(profile.role);
  const [situation, setSituation] = useState(profile.current_situation);

  useEffect(() => {
    setRole(profile.role);
    setSituation(profile.current_situation);
  }, [profile]);

  // Resizing handler
  const isResizingRef = useRef(false);

  const handleMouseDown = (e: React.MouseEvent) => {
    isResizingRef.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingRef.current) return;
      const newWidth = Math.max(260, Math.min(600, e.clientX));
      setSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      if (!isResizingRef.current) return;
      isResizingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      localStorage.setItem('3hmind_sidebar_width', String(sidebarWidth));
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [sidebarWidth, setSidebarWidth]);

  // Handle Profile save manual
  const handleSaveProfile = async () => {
    try {
      await apiCall('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, current_situation: situation, emotional_state: '' })
      });
      onRefreshProfile();
    } catch (e) {
      console.error(e);
    }
  };

  // Add new Goal
  const handleAddGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goalInput.trim()) return;
    try {
      await apiCall('/api/goals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: goalInput.trim(), priority: 1 })
      });
      setGoalInput('');
      onSendAction(''); // trigger load goals implicitly by triggering app re-render via onSendAction stub or manually update
    } catch (e) {
      console.error(e);
    }
  };

  // Add new Ability
  const handleAddAbility = async (e: React.FormEvent) => {
    e.preventDefault();
    const parts = abilityInput.trim().split(/\s+/);
    if (parts.length < 1 || !parts[0]) return;
    const name = parts[0];
    const level = parts[1] || 'beginner';
    try {
      await apiCall('/api/abilities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, level })
      });
      setAbilityInput('');
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="relative flex h-full flex-shrink-0 select-none bg-white/5 backdrop-blur-xl border-r border-white/10 z-10">
      {/* Actual sidebar container */}
      <div
        style={{ width: collapsed ? 0 : sidebarWidth, opacity: collapsed ? 0 : 1 }}
        className="h-full flex flex-col overflow-y-auto overflow-x-hidden transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
      >
        <div className="p-5 flex-1 space-y-7 max-w-full">
          {/* Section: Action Hub */}
          <div className="space-y-3">
            <h3 className="text-2xs font-bold text-white/50 font-mono tracking-widest uppercase flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-blue-400" />
              <span>智能决策中心</span>
            </h3>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => onSendAction('/api/review')}
                className="px-3 py-2.5 text-left text-xs text-white/95 bg-white/5 border border-white/10 rounded-xl hover:border-white/30 hover:bg-white/10 active:scale-95 transition-all text-ellipsis overflow-hidden font-medium cursor-pointer"
              >
                复盘反思
              </button>
              <button
                onClick={onSendPlan}
                className="px-3 py-2.5 text-left text-xs text-white/95 bg-white/5 border border-white/10 rounded-xl hover:border-white/30 hover:bg-white/10 active:scale-95 transition-all text-ellipsis overflow-hidden font-medium cursor-pointer"
              >
                成长方案
              </button>
              <button
                onClick={() => onSendAction('/api/nudge')}
                className="px-3 py-2.5 text-left text-xs text-white/95 bg-white/5 border border-white/10 rounded-xl hover:border-white/30 hover:bg-white/10 active:scale-95 transition-all text-ellipsis overflow-hidden font-medium cursor-pointer"
              >
                主动提问
              </button>
              <button
                onClick={onLoadDashboard}
                className="px-3 py-2.5 text-left text-xs text-white/95 bg-white/5 border border-white/10 rounded-xl hover:border-white/30 hover:bg-white/10 active:scale-95 transition-all text-ellipsis overflow-hidden font-medium cursor-pointer"
              >
                个人大屏
              </button>
            </div>
          </div>

          {/* Section: Input Modes */}
          <div className="space-y-3">
            <h3 className="text-2xs font-bold text-white/50 font-mono tracking-widest uppercase flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-blue-400" />
              <span>多维认知通道接入</span>
            </h3>

            <div className="bg-white/5 p-4 rounded-2xl border border-white/10 space-y-3 shadow-md">
              <div className="space-y-1">
                <span className="text-[10px] text-white/40 font-mono tracking-widest uppercase font-medium">— 现场设备载入</span>
                <div className="grid grid-cols-3 gap-1.5 pt-1">
                  <button
                    onClick={() => onOpenMediaModal('audio')}
                    className="py-2 text-center text-3xs text-white/70 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 hover:text-white hover:border-white/20 active:scale-95 transition-all cursor-pointer flex flex-col items-center gap-1"
                  >
                    <Mic className="w-3.5 h-3.5 text-blue-400" />
                    <span>麦克风录音</span>
                  </button>
                  <button
                    onClick={() => onOpenMediaModal('camera')}
                    className="py-2 text-center text-3xs text-white/70 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 hover:text-white hover:border-white/20 active:scale-95 transition-all cursor-pointer flex flex-col items-center gap-1"
                  >
                    <Camera className="w-3.5 h-3.5 text-purple-400" />
                    <span>摄像头采集</span>
                  </button>
                  <button
                    onClick={() => onOpenMediaModal('document')}
                    className="py-2 text-center text-3xs text-white/70 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 hover:text-white hover:border-white/20 active:scale-95 transition-all cursor-pointer flex flex-col items-center gap-1"
                  >
                    <FileText className="w-3.5 h-3.5 text-emerald-400" />
                    <span>文本类文档</span>
                  </button>
                </div>
              </div>

              <div className="space-y-1 pt-2 border-t border-white/10">
                <span className="text-[10px] text-white/40 font-mono tracking-widest uppercase font-medium">— 神经流式芯片 (预留)</span>
                <div className="grid grid-cols-2 gap-1.5 pt-1">
                  <button
                    onClick={() => onOpenMediaModal('camera_stream')}
                    className="py-1.5 px-2 text-left text-3xs text-white/60 bg-white/5 hover:bg-white/10 border border-dashed border-white/10 rounded-lg hover:text-white transition-all cursor-pointer flex items-center gap-2"
                  >
                    <Video className="w-3 h-3 text-purple-400" />
                    <span className="truncate">外部监控流</span>
                  </button>
                  <button
                    onClick={() => onOpenMediaModal('audio_stream')}
                    className="py-1.5 px-2 text-left text-3xs text-white/60 bg-white/5 hover:bg-white/10 border border-dashed border-white/10 rounded-lg hover:text-white transition-all cursor-pointer flex items-center gap-2"
                  >
                    <Waves className="w-3 h-3 text-blue-400 animate-pulse" />
                    <span className="truncate">外置播音流</span>
                  </button>
                  <button
                    onClick={() => onOpenMediaModal('bci')}
                    className="py-1.5 px-2 text-left text-3xs text-white/60 bg-white/5 hover:bg-white/10 border border-dashed border-white/10 rounded-lg hover:text-white transition-all cursor-pointer flex items-center gap-2"
                  >
                    <BrainCircuit className="w-3 h-3 text-indigo-400" />
                    <span className="truncate">脑机 EEG 接口</span>
                  </button>
                  <button
                    onClick={() => onOpenMediaModal('somatosensory')}
                    className="py-1.5 px-2 text-left text-3xs text-white/60 bg-white/5 hover:bg-white/10 border border-dashed border-white/10 rounded-lg hover:text-white transition-all cursor-pointer flex items-center gap-2"
                  >
                    <Hammer className="w-3 h-3 text-amber-500" />
                    <span className="truncate">体感传感器</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Section: Profile Persona */}
          <div className="space-y-3">
            <h3 className="text-2xs font-bold text-white/50 font-mono tracking-widest uppercase flex items-center gap-1.5">
              <span>心智与个人画像</span>
            </h3>
            <div className="bg-white/5 p-4 rounded-2xl border border-white/10 space-y-3 shadow-md">
              <div className="space-y-1">
                <span className="text-[10px] text-white/40 font-mono tracking-widest uppercase">语义实体标签</span>
                <p className="text-xs text-white/90 leading-relaxed font-sans bg-[#0a0a14]/60 p-3 rounded-xl border border-white/10">
                  {profile.role ? (
                    <>
                      <strong className="text-emerald-400">角色：</strong>{profile.role}
                      <br />
                      <strong className="text-blue-400 mt-1.5 inline-block">处境：</strong>{profile.current_situation}
                    </>
                  ) : (
                    <span className="text-white/30 font-light italic">画像加载中...</span>
                  )}
                </p>
              </div>

              {/* Editable manual override */}
              <div className="space-y-2 pt-2 border-t border-white/10">
                <input
                  type="text"
                  placeholder="修正认知角色 (如 后端工程师)"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg glass-input text-white outline-none placeholder:text-white/20"
                />
                <input
                  type="text"
                  placeholder="输入你当前的关键瓶颈"
                  value={situation}
                  onChange={(e) => setSituation(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg glass-input text-white outline-none placeholder:text-white/20"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleSaveProfile}
                    className="flex-1 py-1.5 bg-white/5 text-white/80 font-semibold border border-white/10 rounded-lg text-3xs hover:bg-white/10 hover:text-white transition-all cursor-pointer"
                  >
                    配置修剪
                  </button>
                  <button
                    onClick={onAskProfileQuestion}
                    className="flex-1 py-1.5 bg-gradient-to-br from-indigo-500/20 to-blue-500/20 text-blue-400 border border-white/10 rounded-lg text-3xs hover:from-indigo-500/30 hover:to-blue-500/30 hover:text-white transition-all flex items-center justify-center gap-1 cursor-pointer"
                    title="触发引导性对话，加深自我洞察"
                  >
                    <HelpCircle className="w-3 h-3" />
                    <span>语义探索</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Section: Deep Dialogue (Inquiry session) */}
          <div className="space-y-3">
            <h3 className="text-2xs font-bold text-white/50 font-mono tracking-widest uppercase flex items-center gap-1.5">
              <MessageSquareText className="w-3.5 h-3.5 text-purple-400" />
              <span>主题深度对话</span>
            </h3>

            <div className="bg-white/5 p-4 rounded-2xl border border-white/10 space-y-3 shadow-md">
              {!inquiryActive ? (
                <div className="space-y-2">
                  <input
                    type="text"
                    placeholder="输入对话主题 (如: 技术栈突破)"
                    value={inquiryTopicInput}
                    onChange={(e) => setInquiryTopicInput(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs rounded-lg glass-input text-white outline-none placeholder:text-white/20"
                  />
                  <button
                    onClick={() => {
                      onStartInquiry(inquiryTopicInput);
                      setInquiryTopicInput('');
                    }}
                    className="w-full py-2 bg-gradient-to-br from-indigo-600/50 to-blue-600/50 hover:from-indigo-600/70 hover:to-blue-600/70 border border-white/10 rounded-xl text-xs font-semibold text-white transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-md"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>启动深度对话</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-blue-400">{inquiryTopic || '主题对话'}</span>
                    <span className="font-mono text-white/40">{inquiryIndex + 1}/{inquiryQuestions.length}</span>
                  </div>

                  {/* Progress tracker bar */}
                  <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all duration-300"
                      style={{ width: `${(inquiryIndex / inquiryQuestions.length) * 100}%` }}
                    />
                  </div>

                  {/* Question steps indicator */}
                  <ul className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1">
                    {inquiryQuestions.map((q, idx) => {
                      const isActive = idx === inquiryIndex;
                      const isAsked = q.asked;
                      return (
                        <li
                          key={idx}
                          className={`p-1.5 rounded-lg border text-3xs flex items-start gap-2 transition-all ${
                            isActive
                              ? 'bg-white/10 border-white/20 text-white font-medium'
                              : isAsked
                              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                              : 'bg-transparent border-transparent text-white/30'
                          }`}
                        >
                          <div
                            className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] flex-shrink-0 ${
                              isActive
                                ? 'bg-blue-500 text-white font-bold'
                                : isAsked
                                ? 'bg-emerald-600 text-white'
                                : 'bg-white/5 border border-white/10 text-white/40 font-mono'
                            }`}
                          >
                            {isAsked ? '✓' : idx + 1}
                          </div>
                          <span className="break-words mt-0.5">{q.text}</span>
                        </li>
                      );
                    })}
                  </ul>

                  {/* Insights counters */}
                  {inquiryInsightsCount > 0 && (
                    <div className="p-1 px-3 text-center rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono text-[10px]">
                      已收集 {inquiryInsightsCount} 条认知洞察流
                    </div>
                  )}

                  <button
                    onClick={onStopInquiry}
                    className="w-full py-1.5 bg-white/5 text-rose-400 border border-rose-500/20 rounded-lg text-xs font-semibold hover:bg-rose-500/15 transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Square className="w-3.5 h-3.5" />
                    <span>结束当前对话</span>
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Section: Action Goals */}
          <div className="space-y-3">
            <h3 className="text-2xs font-bold text-white/50 font-mono tracking-widest uppercase flex items-center gap-1.5">
              <Award className="w-3.5 h-3.5 text-amber-400" />
              <span>动态活跃发展目标</span>
            </h3>

            <div className="space-y-2">
              <AnimatePresence initial={false}>
                {goals.length === 0 ? (
                  <div className="text-xs text-white/30 italic p-4 text-center border border-dashed border-white/10 rounded-xl">
                    建立你的第一个成长路线目标
                  </div>
                ) : (
                  goals.map((g) => {
                    let progressColor = 'bg-amber-500';
                    let progressBorder = 'border-white/10';
                    let progressText = 'text-amber-400';

                    if (g.progress >= 75) {
                      progressColor = 'bg-emerald-500';
                      progressText = 'text-emerald-400';
                    } else if (g.progress >= 30) {
                      progressColor = 'bg-blue-500';
                      progressText = 'text-blue-400';
                    }

                    return (
                      <motion.div
                        key={g.id}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        onClick={() => onAdvanceGoal(g.id, g.progress)}
                        className={`bg-white/5 p-4 rounded-2xl border ${progressBorder} space-y-2.5 hover:border-white/20 hover:bg-white/10 cursor-pointer group transition-all shadow-md`}
                        title="点击推进目标完工线25%"
                      >
                        <div className="flex justify-between items-center text-[10px] font-mono text-white/40">
                          <span className="flex items-center gap-1 font-medium">
                            <Milestone className="w-3 h-3 text-white/30" />
                            成长中
                          </span>
                          <span>PRIORITY {g.priority || 1}</span>
                        </div>

                        <div className="flex justify-between items-start gap-2">
                          <span className="text-xs font-semibold text-white/95 line-clamp-2 leading-tight group-hover:text-white transition-colors">
                            {g.goal}
                          </span>
                          <span className={`text-xs font-bold font-mono ${progressText}`}>{g.progress}%</span>
                        </div>

                        {/* Progress Meter Slider */}
                        <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${progressColor}`}
                            style={{ width: `${g.progress}%` }}
                          />
                        </div>

                        {/* Star assessment button overlay */}
                        <div className="flex items-center justify-end gap-1.5 pt-1 opacity-50 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onAssessGoal(g.id);
                            }}
                            className="p-1 rounded bg-white/5 text-amber-400 hover:text-amber-200 hover:bg-white/10 active:scale-90 transition-all cursor-pointer border border-white/10"
                            title="由成长主理人专家进行4维全域性数据评审与归纳"
                          >
                            <Sparkles className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onDeleteGoal(g.id);
                            }}
                            className="p-1 rounded bg-white/5 text-white/40 hover:text-rose-400 hover:bg-white/10 active:scale-90 transition-all cursor-pointer border border-white/10"
                            title="裁撤并清除此项目标"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </motion.div>
                    );
                  })
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Section: Dynamic Adders */}
          <div className="space-y-3">
            <h3 className="text-2xs font-bold text-white/50 font-mono tracking-widest uppercase flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-sky-400" />
              <span>载入新指标</span>
            </h3>

            <div className="space-y-2">
              <form onSubmit={handleAddGoal} className="relative">
                <input
                  type="text"
                  placeholder="创建并定位路线新目标..."
                  value={goalInput}
                  onChange={(e) => setGoalInput(e.target.value)}
                  className="w-full pl-3 pr-8 py-2 text-xs rounded-lg glass-input text-white outline-none placeholder:text-white/20"
                />
                <button
                  type="submit"
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 text-white/40 hover:text-white transition-colors cursor-pointer"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </form>

              <form onSubmit={handleAddAbility} className="relative">
                <input
                  type="text"
                  placeholder="载入技能实体 (如: Next.js expert)"
                  value={abilityInput}
                  onChange={(e) => setAbilityInput(e.target.value)}
                  className="w-full pl-3 pr-8 py-2 text-xs rounded-lg glass-input text-white outline-none placeholder:text-white/20"
                />
                <button
                  type="submit"
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 text-white/40 hover:text-white transition-colors cursor-pointer"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>

      {/* Resize Handle and toggle */}
      <div
        onMouseDown={handleMouseDown}
        className="group relative w-[3px] h-full hover:w-1 bg-white/5 hover:bg-blue-500/30 cursor-col-resize active:bg-blue-400 transition-all flex items-center justify-center animate-pulse"
      >
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="absolute left-1/2 -translate-x-1/2 w-5 h-9 bg-white/10 backdrop-blur-md border border-white/15 rounded-md flex items-center justify-center text-white/60 hover:text-white hover:bg-white/20 transition-all shadow shadow-black/40 z-25 cursor-pointer"
        >
          {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
        </button>
      </div>
    </div>
  );
}
