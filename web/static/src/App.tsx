import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Message, Goal, Profile, InquiryQuestion, ConvState } from './types';
import LoginOverlay from './components/LoginOverlay';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import ChatInput from './components/ChatInput';
import Modals from './components/Modals';

export default function App() {
  // Global Session
  const [authToken, setAuthToken] = useState<string>(() => localStorage.getItem('3hmind_token') || '');
  const [currentUser, setCurrentUser] = useState<string>('');

  // Core States
  const [messages, setMessages] = useState<Message[]>([]);
  const [profile, setProfile] = useState<Profile>({ role: '', current_situation: '', emotional_state: '' });
  const [goals, setGoals] = useState<Goal[]>([]);
  const [convState, setConvState] = useState<ConvState>('idle');
  const [voiceTranscript, setVoiceTranscript] = useState('');
  const [convMode, setConvMode] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(true);
  const [autoAsk, setAutoAsk] = useState(true);
  const [activeSpeakingId, setActiveSpeakingId] = useState<string | null>(null);

  // Layout sizing
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem('3hmind_sidebar_width');
    return saved ? Number(saved) : 280;
  });

  // Modal manager
  const [mediaModalOpen, setMediaModalOpen] = useState(false);
  const [mediaModalTab, setMediaModalTab] = useState('document');

  // Deep Inquiry/Dialogue State
  const [inquiryActive, setInquiryActive] = useState(false);
  const [inquiryQuestions, setInquiryQuestions] = useState<InquiryQuestion[]>([]);
  const [inquiryIndex, setInquiryIndex] = useState(0);
  const [inquiryTopic, setInquiryTopic] = useState('');
  const [waitingForInquiryAnswer, setWaitingForInquiryAnswer] = useState(false);
  const [inquiryInsightsCount, setInquiryInsightsCount] = useState(0);

  // References for Async & Speech API states
  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaChunksRef = useRef<Blob[]>([]);

  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const followUpTimerRef = useRef<NodeJS.Timeout | null>(null);
  const typingWatchTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Speech Queue references
  const ttsQueueRef = useRef<string[]>([]);
  const ttsBusyRef = useRef<boolean>(false);
  const ttsSpokenLenRef = useRef<number>(0);
  const micGatedRef = useRef<boolean>(false);
  const synthRef = useRef<SpeechSynthesis>(window.speechSynthesis);
  const synthVoiceRef = useRef<SpeechSynthesisVoice | null>(null);

  // Continuous loop pointers
  const lastUserMsgRef = useRef('');
  const lastAiResponseRef = useRef('');
  const followUpCountRef = useRef(0);
  const voiceTranscriptRef = useRef('');
  const voiceFinalTextRef = useRef('');
  const silenceCountdownRef = useRef(0);
  const silentCyclesRef = useRef(0);
  const useMediaRecorderRef = useRef(false);
  const voiceInputActiveRef = useRef(false);
  const voicePausedRef = useRef(false);
  const prevTypedTextRef = useRef('');
  const hasSpokenRef = useRef(false);

  // Detection lists
  const SENTENCE_END_PATTERNS = [
    /[吗呢吧啊呀哦嘛咯]$/,
    /[？?！!。，,～~]$/,
    /什么$/, /怎么$/, /为什么$/,
    /多少$/, /哪[个些种边]$/, /谁$/,
    /[了的]$/,
    /[好行对可]$/,
    /是不是$/, /能不能$/, /会不会$/, /可不可以$/,
    /[过完到]$/,
    /就这样$/, /这样做$/, /没问题$/,
    /[吧嘛][。！？]?$/,
    /.{0,2}[。！？]$/
  ];

  const STOP_PHRASES = [
    '不要说了', '别说了', '停止', '闭嘴', '别问了', '不要问了',
    '关闭对话', '关闭语音', '结束对话', '再见', '拜拜', '休息吧',
    '不要沟通了', '不聊了', '别沟通了', '停止沟通',
  ];

  const VOICE_INPUT_END_PHRASES = [
    '说完了', '就这样', '完毕', '好了', '可以了',
    '就这些', '先这样', '讲完了', '就到这里',
    '以上', '发送', '确认发送',
  ];

  // API wrapper helper
  const apiCall = useCallback(async (path: string, options: RequestInit = {}) => {
    const headers = { ...((options.headers as Record<string, string>) || {}) };
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    }
    const resp = await fetch(path, { ...options, headers });
    if (resp.status === 401) {
      handleLogout();
      throw new Error('Unauthorized');
    }
    return resp;
  }, [authToken]);

  // Handle addition of custom system logs
  const addMessage = useCallback((text: string, role: 'user' | 'agent' | 'system', isStreaming = false) => {
    const newMsg: Message = {
      id: Math.random().toString(36).substring(7),
      text,
      role,
      timestamp: new Date(),
      isStreaming,
    };
    setMessages((prev) => [...prev, newMsg]);
    return newMsg;
  }, []);

  // Text-To-Speech Single playing
  const speakTextOne = (text: string): Promise<void> => {
    return new Promise((resolve) => {
      if (!autoSpeak) return resolve();
      const clean = text.replace(/[【】\[\]=#\-\*～\n]+/g, ' ').trim();
      if (!clean) return resolve();

      const u = new SpeechSynthesisUtterance(clean);
      if (synthVoiceRef.current) u.voice = synthVoiceRef.current;
      u.lang = 'zh-CN';
      u.rate = 1.45;
      u.pitch = 1.0;

      u.onend = () => resolve();
      u.onerror = () => resolve();

      synthRef.current.resume();
      synthRef.current.speak(u);
    });
  };

  const speakText = async (text: string, msgId?: string) => {
    if (!autoSpeak || !text) return;
    if (synthRef.current.speaking) synthRef.current.cancel();

    micGatedRef.current = true;
    stopSpeechRecognitionOnly();

    if (msgId) setActiveSpeakingId(msgId);

    const clean = text.replace(/[【】\[\]=#\-\*～\n]+/g, ' ').substring(0, 2000);
    await speakTextOne(clean);

    setActiveSpeakingId(null);
    setTimeout(() => {
      micGatedRef.current = false;
    }, 200);
  };

  // Streaming speech synthesis segments dispatcher
  const ttsResetQueue = () => {
    ttsQueueRef.current = [];
    ttsBusyRef.current = false;
    ttsSpokenLenRef.current = 0;
  };

  const ttsFlushQueue = async () => {
    if (ttsBusyRef.current) return;
    while (ttsQueueRef.current.length > 0) {
      const segment = ttsQueueRef.current.shift();
      if (segment) {
        ttsBusyRef.current = true;
        await speakTextOne(segment);
        ttsBusyRef.current = false;
      }
    }
  };

  const ttsSliceSentences = (text: string) => {
    const newText = text.slice(ttsSpokenLenRef.current);
    const parts: string[] = [];
    let lastEnd = 0;
    const SENTENCE_RE = /[。！？.!?\n]/;

    for (let i = 0; i < newText.length; i++) {
      if (SENTENCE_RE.test(newText[i])) {
        parts.push(newText.slice(lastEnd, i + 1));
        lastEnd = i + 1;
      }
    }
    if (lastEnd > 0) ttsSpokenLenRef.current += lastEnd;
    return parts;
  };

  // Profile data fetchers
  const checkProfileStatus = useCallback(async () => {
    try {
      const resp = await apiCall('/api/profile/status');
      if (resp.ok) {
        const data = await resp.json();
        setProfile(data.profile || { role: '', current_situation: '', emotional_state: '' });
      }
    } catch (e) {}
  }, [apiCall]);

  const loadGoals = useCallback(async () => {
    try {
      const resp = await apiCall('/api/goals');
      if (resp.ok) {
        const data = await resp.json();
        setGoals(data || []);
      }
    } catch (e) {}
  }, [apiCall]);

  // Setup basic account loads
  const loadWorkspace = useCallback(() => {
    checkProfileStatus();
    loadGoals();
  }, [checkProfileStatus, loadGoals]);

  const onLoginSuccess = (token: string, username: string) => {
    localStorage.setItem('3hmind_token', token);
    setAuthToken(token);
    setCurrentUser(username);
  };

  const handleLogout = () => {
    localStorage.removeItem('3hmind_token');
    setAuthToken('');
    setCurrentUser('');
    setMessages([]);
    stopAll();
  };

  // Polling updates
  useEffect(() => {
    if (!authToken) return;

    const interval = setInterval(async () => {
      if (convMode && convState !== 'idle') return;
      try {
        const resp = await apiCall('/api/poll');
        if (resp.ok) {
          const data = await resp.json();
          if (data.reflection) {
            const msg = addMessage('[自主复盘]\n' + data.reflection, 'agent');
            if (autoSpeak) speakText('[自主复盘]\n' + data.reflection, msg.id);
          }
          if (data.nudge) {
            const msg = addMessage('[自主提醒]\n' + data.nudge, 'agent');
            if (autoSpeak) speakText('[自主提醒]\n' + data.nudge, msg.id);
          }
        }
      } catch (e) {}
    }, 15000);

    return () => clearInterval(interval);
  }, [authToken, convMode, convState, autoSpeak, apiCall, addMessage]);

  // Handlers for goals
  const handleDeleteGoal = async (id: number) => {
    try {
      await apiCall(`/api/goals/${id}`, { method: 'DELETE' });
      loadGoals();
    } catch (e) {}
  };

  const handleAdvanceGoal = async (id: number, currentPct: number) => {
    const nextPct = currentPct >= 100 ? 0 : Math.min(100, currentPct + 25);
    try {
      await apiCall(`/api/goals/${id}/progress`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ progress: nextPct })
      });
      loadGoals();
    } catch (e) {}
  };

  const handleAssessGoal = async (id: number) => {
    addMessage('正在深度分析对目标的客观达成路线...', 'system');
    setConvState('processing');
    try {
      const resp = await apiCall(`/api/goals/${id}/assess`, { method: 'POST' });
      if (resp.ok) {
        const data = await resp.json();
        setConvState('idle');

        // Render assessment format
        const dims = data.dimension_scores || {};
        const dimStr = Object.entries(dims).map(([k, v]: [string, any]) => {
          const blocks = '■'.repeat(Math.round(v.score / 10)) + '□'.repeat(10 - Math.round(v.score / 10));
          return `${k}: ${blocks} ${v.score}分 (权重 ${(v.weight * 100).toFixed(0)}%)`;
        }).join('\n');

        const sugStr = (data.suggestions || []).map((s: any) => `▶ ${s.dimension}: ${s.action} (方法: ${s.method || '自主探索'})`).join('\n');

        const report = `[目标全域专家诊断报告]\n${data.feedback || '系统匹配完成'}\n\n多维状态：\n${dimStr}\n\n改进建议：\n${sugStr}`;
        addMessage(report, 'agent');
        if (autoSpeak) speakText('报告已生成。');
        loadGoals();
      }
    } catch (e) {
      setConvState('idle');
    }
  };

  // Detection indicators
  const detectSentenceEnd = (text: string) => {
    if (!text || text.length < 3) return false;
    const t = text.trim();
    return SENTENCE_END_PATTERNS.some(p => p.test(t));
  };

  const detectStopIntent = (text: string) => {
    const t = text.toLowerCase().replace(/\s+/g, '');
    return STOP_PHRASES.some(p => t.includes(p));
  };

  const detectVoiceEndPhrase = (text: string) => {
    if (!text || text.length < 3) return false;
    const t = text.replace(/\s+/g, '');
    return VOICE_INPUT_END_PHRASES.some(p => t.includes(p));
  };

  // Silence trackers
  const clearSilenceTimer = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
    silenceCountdownRef.current = 0;
  };

  const handleSilenceTimeout = () => {
    clearSilenceTimer();
    const txt = voiceTranscriptRef.current.trim();

    if (convMode) {
      if (txt && txt.length >= 2) {
        if (detectStopIntent(txt)) {
          stopSpeechRecognitionOnly();
          addMessage(`[语音] ${txt}`, 'user');
          addMessage('[系统] 检测到停止意图，已挂载退出。', 'system');
          toggleConversationMode();
          return;
        }
        voiceInputActiveRef.current = false;
        stopSpeechRecognitionOnly();
        hasSpokenRef.current = false;
        finishVoiceInput();
      } else {
        if (convState === 'listening') {
          stopSpeechRecognitionOnly();
          hasSpokenRef.current = false;
          silentCyclesRef.current++;

          if (silentCyclesRef.current >= 3) {
            silentCyclesRef.current = 0;
            setConvState('idle');
            if (autoAsk) scheduleProactiveInquiry();
          } else {
            // Keep silent cycle listening loop
            setTimeout(() => {
              if (convMode && convState === 'idle') startListening();
            }, 300);
          }
        }
      }
    } else if (txt && txt.length >= 2) {
      voiceInputActiveRef.current = false;
      stopSpeechRecognitionOnly();
      finishVoiceInput();
    } else {
      setConvState('idle');
    }
  };

  const resetSilenceTimer = () => {
    clearSilenceTimer();
    const acc = voiceTranscriptRef.current.trim();
    const isComplete = detectSentenceEnd(acc);
    const timeout = isComplete ? 3 : 4; // short vs long countdown

    silenceCountdownRef.current = timeout;
    countdownIntervalRef.current = setInterval(() => {
      silenceCountdownRef.current--;
      if (silenceCountdownRef.current <= 0) {
        clearSilenceTimer();
        handleSilenceTimeout();
      }
    }, 1000);

    silenceTimerRef.current = setTimeout(() => {
      handleSilenceTimeout();
    }, timeout * 1000);
  };

  const stopSpeechRecognitionOnly = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (err) {}
      recognitionRef.current = null;
    }
    clearSilenceTimer();
  };

  // Standard Continuous / Speech Web API loader
  const startListening = (keepText = false) => {
    if (useMediaRecorderRef.current) {
      startMediaRecorder();
      return;
    }

    // Guard gating synthesis
    if (micGatedRef.current) {
      let retries = 0;
      const poll = () => {
        if (!micGatedRef.current && convMode && convState === 'idle') {
          startListening();
        } else if (retries < 6 && convMode) {
          retries++;
          setTimeout(poll, 250);
        }
      };
      setTimeout(poll, 250);
      return;
    }

    voicePausedRef.current = false;
    clearTypingTimer();

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    if (synthRef.current.speaking) synthRef.current.cancel();

    if (!keepText) {
      voiceTranscriptRef.current = '';
      setVoiceTranscript('');
    }

    const rec = new SpeechRecognition();
    rec.lang = 'zh-CN';
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      voiceInputActiveRef.current = true;
      if (!keepText) {
        voiceFinalTextRef.current = '';
      }
      setConvState('listening');
      resetSilenceTimer();
    };

    rec.onresult = (event: any) => {
      hasSpokenRef.current = true;
      silentCyclesRef.current = 0;
      clearProactiveTimer();
      resetSilenceTimer();

      let finalText = '';
      let interimText = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          finalText += event.results[i][0].transcript;
        } else {
          interimText += event.results[i][0].transcript;
        }
      }
      if (finalText) {
        voiceTranscriptRef.current += finalText;
      }
      const fullText = voiceTranscriptRef.current + interimText;
      voiceFinalTextRef.current = fullText;
      setVoiceTranscript(fullText);

      // Realtime stop intent trigger
      if (detectStopIntent(fullText)) {
        stopSpeechRecognitionOnly();
        addMessage(`[系统] 语音识别命中停止标志。正在重置会话。`, 'system');
        stopAll();
        return;
      }

      // Voice complete trigger
      if (detectVoiceEndPhrase(voiceTranscriptRef.current)) {
        clearSilenceTimer();
        voiceInputActiveRef.current = false;
        stopSpeechRecognitionOnly();
        finishVoiceInput();
      }
    };

    rec.onerror = (event: any) => {
      if (event.error === 'no-speech' || event.error === 'aborted') return;
      stopSpeechRecognitionOnly();
      setConvState('idle');

      // Network fallback triggers MediaRecorder
      if (event.error === 'network' || event.error === 'not-allowed') {
        useMediaRecorderRef.current = true;
        addMessage('[系统] 浏览器云 Speech 通道遇到限制，自动降级为全录音 Whisper 模型', 'system');
        if (convMode) {
          setTimeout(() => {
            if (convMode && convState === 'idle') startMediaRecorder();
          }, 1000);
        }
      }
    };

    rec.onend = () => {
      if (convMode && convState === 'listening' && !voicePausedRef.current) {
        // Continuous listening reboot
        setTimeout(() => {
          if (convMode && convState === 'listening') startListening(true);
        }, 800);
      }
    };

    recognitionRef.current = rec;
    try {
      rec.start();
    } catch (e) {
      setTimeout(() => {
        if (convMode && convState === 'listening') startListening();
      }, 1500);
    }
  };

  // MediaRecorder backup Whisper STT
  const startMediaRecorder = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';

      const rec = new MediaRecorder(stream, { mimeType: mime });
      mediaChunksRef.current = [];

      rec.ondataavailable = (e) => {
        if (e.data.size > 0) mediaChunksRef.current.push(e.data);
      };

      rec.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        if (mediaChunksRef.current.length === 0) return;

        const blob = new Blob(mediaChunksRef.current, { type: mime });
        mediaChunksRef.current = [];

        // Post audio bytes up
        setConvState('processing');
        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');

        try {
          const resp = await apiCall('/api/stt', { method: 'POST', body: formData });
          if (resp.ok) {
            const data = await resp.json();
            if (data.text?.trim()) {
              voiceFinalTextRef.current = data.text.trim();
              finishVoiceInput();
            } else {
              setConvState('idle');
              if (convMode) startMediaRecorder();
            }
          }
        } catch (e) {
          setConvState('idle');
        }
      };

      mediaRecorderRef.current = rec;
      rec.start(250);
      voiceInputActiveRef.current = true;
      setConvState('listening');
    } catch (err) {
      useMediaRecorderRef.current = false;
    }
  };

  const stopMediaRecorder = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  };

  const toggleMic = () => {
    if (convState === 'listening') {
      if (convMode) {
        // Pause continuously mode temporarily, start standard keyboard typing watcher
        voicePausedRef.current = true;
        setConvState('idle');
        stopSpeechRecognitionOnly();
        stopMediaRecorder();
        triggerTypingWatch();
      } else {
        stopSpeechRecognitionOnly();
        stopMediaRecorder();
        setConvState('idle');
      }
    } else if (!micGatedRef.current) {
      voicePausedRef.current = false;
      clearTypingTimer();
      startListening();
    }
  };

  const triggerTypingWatch = () => {
    clearTypingTimer();
    typingWatchTimerRef.current = setTimeout(() => {
      if (convMode && voicePausedRef.current) {
        voicePausedRef.current = false;
        startListening();
      }
    }, 5000); // resumes speech captures if keyboard action halts for 5 seconds
  };

  const clearTypingTimer = () => {
    if (typingWatchTimerRef.current) {
      clearTimeout(typingWatchTimerRef.current);
      typingWatchTimerRef.current = null;
    }
  };

  // Optimized Speech Transcriber Refiner and Dispatcher
  const finishVoiceInput = async () => {
    const raw = (voiceFinalTextRef.current || voiceTranscriptRef.current || '').trim();
    if (!raw || raw.length < 2) {
      setConvState('idle');
      if (convMode) setTimeout(() => startListening(), 600);
      return;
    }

    setConvState('processing');
    try {
      // POST out to semantic refiner
      const resp = await apiCall('/api/voice/refine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: raw })
      });
      const data = await resp.json();
      const refined = data.refined || raw;

      voiceTranscriptRef.current = '';
      voiceFinalTextRef.current = '';
      setVoiceTranscript('');

      sendStreamChat(refined);
    } catch (e) {
      voiceTranscriptRef.current = '';
      voiceFinalTextRef.current = '';
      setVoiceTranscript('');
      sendStreamChat(raw);
    }
  };

  // Message submission - SSE streaming text channel
  const sendStreamChat = async (msgText: string) => {
    if (inquiryActive && waitingForInquiryAnswer) {
      sendInquiryAnswer(msgText);
      return;
    }

    addMessage(msgText, 'user');
    setConvState('processing');

    // Create streaming text container
    const tempId = Math.random().toString(36).substring(7);
    const streamingMsg: Message = {
      id: tempId,
      text: '',
      role: 'agent',
      timestamp: new Date(),
      isStreaming: true,
    };

    setMessages((prev) => [...prev, streamingMsg]);

    ttsResetQueue();

    let fullOutput = '';
    let buffer = '';

    try {
      const resp = await apiCall('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msgText, context_type: 'voice' }),
      });

      if (!resp.body) throw new Error('Empty response payload');
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.token) {
                fullOutput += data.token;
                // Update stream in state
                setMessages((prev) =>
                  prev.map((m) => (m.id === tempId ? { ...m, text: fullOutput } : m))
                );

                // Incremental voice sentences dispatcher
                const freshSentences = ttsSliceSentences(fullOutput);
                if (freshSentences.length > 0) {
                  if (autoSpeak) {
                    micGatedRef.current = true;
                    stopSpeechRecognitionOnly();
                    setConvState('speaking');
                    setActiveSpeakingId(tempId);
                  }
                  freshSentences.forEach((s) => ttsQueueRef.current.push(s));
                  ttsFlushQueue();
                }
              }
            } catch (err) {}
          }
        }
      }
    } catch (e) {
      fullOutput = '思维信道异常，加载失败。';
    }

    // Flush any remaining slices
    const remaining = fullOutput.slice(ttsSpokenLenRef.current).trim();
    if (remaining) {
      if (autoSpeak) {
        micGatedRef.current = true;
        stopSpeechRecognitionOnly();
        setConvState('speaking');
        setActiveSpeakingId(tempId);
      }
      ttsQueueRef.current.push(remaining);
      await ttsFlushQueue();
    }

    // Remove streaming flag and cleanup
    setMessages((prev) =>
      prev.map((m) => (m.id === tempId ? { ...m, isStreaming: false } : m))
    );
    setActiveSpeakingId(null);
    micGatedRef.current = false;

    lastUserMsgRef.current = msgText;
    lastAiResponseRef.current = fullOutput;

    loadWorkspace();

    if (convMode) {
      setConvState('idle');
      startListening();
    } else {
      setConvState('idle');
    }

    if (autoAsk) scheduleProactiveInquiry();
  };

  // Keyboard text submitting proxy helper
  const handleSendText = (text: string) => {
    sendStreamChat(text);
  };

  // AI Proactive Inquiry scheduler
  const clearProactiveTimer = () => {
    if (followUpTimerRef.current) {
      clearTimeout(followUpTimerRef.current);
      followUpTimerRef.current = null;
    }
  };

  const scheduleProactiveInquiry = () => {
    clearProactiveTimer();
    if (followUpCountRef.current >= 3) return;

    const delay = [12, 18, 25][followUpCountRef.current] * 1000;
    followUpTimerRef.current = setTimeout(async () => {
      await fireProactiveAsk();
    }, delay);
  };

  const fireProactiveAsk = async () => {
    if (followUpCountRef.current >= 3) return;
    followUpCountRef.current++;

    try {
      const resp = await apiCall('/api/proactive/question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          last_user_msg: lastUserMsgRef.current,
          last_ai_response: lastAiResponseRef.current
        })
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.question) {
          const msg = addMessage(`[追问 ${followUpCountRef.current}/3] ${data.question}`, 'agent');
          await speakText(data.question, msg.id);

          if (convMode) {
            setConvState('idle');
            startListening();
          }
          scheduleProactiveInquiry();
        }
      }
    } catch (e) {
      scheduleProactiveInquiry();
    }
  };

  // Deep Inquiry / Dialogue Sessions
  const handleStartInquiry = async (topic: string) => {
    addMessage(`[主题对话] 正在针对该主题生成结构化问题链，请稍后...`, 'system');
    setConvState('processing');

    try {
      const resp = await apiCall('/api/inquiry/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic })
      });
      if (resp.ok) {
        const data = await resp.json();
        setInquiryActive(true);
        setInquiryQuestions(data.questions || []);
        setInquiryIndex(0);
        setInquiryTopic(data.topic || topic);
        setWaitingForInquiryAnswer(true);
        setConvState('idle');

        addMessage(`[系统] 深度研究项目”${data.topic || topic}”正式启动！`, 'system');
        const firstQ = data.questions?.[0]?.text || '我们准备好了，请开始描绘您的核心想法';
        const qMsg = addMessage(firstQ, 'agent');
        await speakText(firstQ, qMsg.id);

        if (convMode) startListening();
      }
    } catch (e) {
      setConvState('idle');
    }
  };

  const sendInquiryAnswer = async (answer: string) => {
    setWaitingForInquiryAnswer(false);
    addMessage(answer, 'user');
    setConvState('processing');

    try {
      const resp = await apiCall('/api/inquiry/next', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer })
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.done) {
          setInquiryActive(false);
          setInquiryQuestions([]);
          setInquiryIndex(0);
          setInquiryTopic('');
          setWaitingForInquiryAnswer(false);
          setConvState('idle');

          const summary = data.summary || '主题评估结束';
          const summaryMsg = addMessage(summary, 'agent');
          await speakText(summary, summaryMsg.id);
          loadWorkspace();
          return;
        }

        setInquiryIndex(data.index);
        // implicit load questions summary
        const qResp = await apiCall('/api/inquiry/status');
        if (qResp.ok) {
          const qStatus = await qResp.json();
          setInquiryInsightsCount(qStatus.insights_count || 0);
          // Refresh list maps
          if (qStatus.active) {
            setInquiryQuestions(qStatus.questions || []);
          }
        }

        const block = data.acknowledgment ? `${data.acknowledgment}\n\n${data.question}` : data.question;
        const blockMsg = addMessage(block, 'agent');
        await speakText(block, blockMsg.id);

        setWaitingForInquiryAnswer(true);
        setConvState('idle');
        if (convMode) startListening();
      }
    } catch (e) {
      setConvState('idle');
      setWaitingForInquiryAnswer(true);
    }
  };

  const handleStopInquiry = async () => {
    try {
      const resp = await apiCall('/api/inquiry/stop', { method: 'POST' });
      if (resp.ok) {
        const data = await resp.json();
        if (data.summary) {
          const sMsg = addMessage(`[主题复习] ${data.summary}`, 'agent');
          await speakText(data.summary, sMsg.id);
        }
      }
    } catch (e) {}

    setInquiryActive(false);
    setInquiryQuestions([]);
    setInquiryIndex(0);
    setInquiryTopic('');
    setWaitingForInquiryAnswer(false);
    setInquiryInsightsCount(0);
    setConvState('idle');
    loadWorkspace();
  };

  const handleAskProfileQuestion = async () => {
    addMessage('[系统] 正在准备生成下一个情境画像探寻问题...', 'system');
    setConvState('processing');
    try {
      const resp = await apiCall('/api/profile/discover');
      if (resp.ok) {
        const data = await resp.json();
        setConvState('idle');
        if (data.question) {
          const pMsg = addMessage(data.question, 'agent');
          await speakText(data.question, pMsg.id);
        }
      }
    } catch (e) {
      setConvState('idle');
    }
  };

  // Global Killswitch
  const stopAll = () => {
    stopSpeechRecognitionOnly();
    stopMediaRecorder();

    if (synthRef.current.speaking) {
      synthRef.current.cancel();
    }

    ttsResetQueue();
    clearSilenceTimer();
    clearProactiveTimer();
    clearTypingTimer();

    micGatedRef.current = false;
    voiceInputActiveRef.current = false;
    useMediaRecorderRef.current = false;
    voicePausedRef.current = false;

    setActiveSpeakingId(null);
    setConvState('idle');
    setConvMode(false);
  };

  // Header helpers
  const toggleAutoSpeak = () => {
    setAutoSpeak(!autoSpeak);
    if (autoSpeak) {
      if (synthRef.current.speaking) synthRef.current.cancel();
      setActiveSpeakingId(null);
    }
  };

  const toggleAutoAsk = () => {
    setAutoAsk(!autoAsk);
    if (autoAsk) {
      clearProactiveTimer();
    }
  };

  const toggleConversationMode = () => {
    if (convMode) {
      setConvMode(false);
      voicePausedRef.current = false;
      clearTypingTimer();
      stopSpeechRecognitionOnly();
      stopMediaRecorder();
      setConvState('idle');
      addMessage('[系统] 连续在线拾音交互已经退出', 'system');
    } else {
      setConvMode(true);
      voicePausedRef.current = false;
      setConvState('idle');
      addMessage('[系统] 连续在线拾音交互启动中... 请直接开始说话。', 'system');
      setTimeout(() => startListening(), 400);
    }
  };

  // Bootstraper
  useEffect(() => {
    const initAuthentication = async () => {
      const localToken = localStorage.getItem('3hmind_token') || '';
      if (!localToken) return;

      try {
        const resp = await fetch('/api/auth/me', {
          headers: { 'Authorization': `Bearer ${localToken}` }
        });
        if (resp.ok) {
          const data = await resp.json();
          setAuthToken(localToken);
          setCurrentUser(data.username);
        } else {
          localStorage.removeItem('3hmind_token');
          setAuthToken('');
        }
      } catch (err) {
        // network issue, gracefully stay offline
      }
    };

    initAuthentication();
  }, []);

  useEffect(() => {
    if (authToken) {
      loadWorkspace();
    }
  }, [authToken, loadWorkspace]);

  // Restore session chat logs if exist
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem('3hmind_chat_react');
      if (saved) {
        const list = JSON.parse(saved);
        setMessages(list.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) })));
      }
    } catch (e) {}
  }, []);

  // Auto-save messages to sessionStorage (debounced, skips during streaming)
  const prevSaveRef = useRef<string>('');
  useEffect(() => {
    const nonStreaming = messages.filter(m => !m.isStreaming);
    const json = JSON.stringify(nonStreaming);
    if (json === prevSaveRef.current) return;
    prevSaveRef.current = json;
    const timer = setTimeout(() => {
      try { sessionStorage.setItem('3hmind_chat_react', json); } catch (e) {}
    }, 300);
    return () => clearTimeout(timer);
  }, [messages]);

  return (
    <div className="flex flex-col h-screen w-screen bg-[#0a0a14] text-white font-sans overflow-hidden relative">
      {/* Background Mesh Gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-600/15 rounded-full blur-[120px] pointer-events-none z-0" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-purple-600/15 rounded-full blur-[120px] pointer-events-none z-0" />
      <div className="absolute top-[20%] right-[10%] w-[30%] h-[40%] bg-indigo-500/10 rounded-full blur-[100px] pointer-events-none z-0" />

      <AnimatePresence>
        {!authToken && (
          <LoginOverlay onLoginSuccess={onLoginSuccess} apiCall={apiCall} />
        )}
      </AnimatePresence>

      {authToken && (
        <div className="flex flex-col h-full w-full z-10">
          {/* Top Panel Cluster */}
          <Header
            currentUser={currentUser}
            autoSpeak={autoSpeak}
            onToggleAutoSpeak={toggleAutoSpeak}
            autoAsk={autoAsk}
            onToggleAutoAsk={toggleAutoAsk}
            convMode={convMode}
            onToggleConvMode={toggleConversationMode}
            convState={convState}
            onStopAll={stopAll}
            onLogout={handleLogout}
            inquiryActive={inquiryActive}
          />

          <div className="flex flex-1 overflow-hidden relative">
            {/* Resizable Left Dashboard Drawer */}
            <Sidebar
              apiCall={apiCall}
              profile={profile}
              onRefreshProfile={checkProfileStatus}
              onSendAction={async (url) => {
                if (!url) { loadGoals(); return; }
                try {
                  const r = await apiCall(url, { method: 'POST' });
                  const data = await r.json();
                  addMessage(data.result || data.nudge || data.message || data.reflection || '操作完成。', 'agent');
                } catch (e) {}
                loadWorkspace();
              }}
              onSendPlan={() => apiCall('/api/plan', { method: 'POST' }).then(async (r) => {
                const data = await r.json();
                addMessage(data.result || '方案制作完成。', 'agent');
                loadWorkspace();
              })}
              onLoadDashboard={async () => {
                setConvState('processing');
                const r = await apiCall('/api/dashboard');
                const data = await r.json();
                setConvState('idle');
                addMessage(data.result || '未生成面板。', 'agent');
              }}
              onOpenMediaModal={(tab) => {
                setMediaModalTab(tab);
                setMediaModalOpen(true);
              }}
              onAskProfileQuestion={handleAskProfileQuestion}
              inquiryActive={inquiryActive}
              inquiryQuestions={inquiryQuestions}
              inquiryIndex={inquiryIndex}
              inquiryTopic={inquiryTopic}
              waitingForInquiryAnswer={waitingForInquiryAnswer}
              onStartInquiry={handleStartInquiry}
              onStopInquiry={handleStopInquiry}
              inquiryInsightsCount={inquiryInsightsCount}
              goals={goals}
              onLoadGoals={loadGoals}
              onDeleteGoal={handleDeleteGoal}
              onAdvanceGoal={handleAdvanceGoal}
              onAssessGoal={handleAssessGoal}
              sidebarWidth={sidebarWidth}
              setSidebarWidth={setSidebarWidth}
            />

            {/* Main Interactive Chat Flow Canvas */}
            <div className="flex-1 flex flex-col justify-between overflow-hidden bg-white/[0.01] backdrop-blur-[2px] relative">
              <ChatArea
                messages={messages}
                activeSpeakingId={activeSpeakingId}
                onSpeakMessage={(id, text) => {
                  if (activeSpeakingId === id) {
                    synthRef.current.cancel();
                    ttsResetQueue();
                    setActiveSpeakingId(null);
                    setConvState('idle');
                    micGatedRef.current = false;
                  } else {
                    speakText(text, id);
                  }
                }}
                convState={convState}
              />

              <ChatInput
                onSendText={handleSendText}
                onToggleMic={toggleMic}
                onOpenMediaModal={() => {
                  setMediaModalTab('document');
                  setMediaModalOpen(true);
                }}
                convState={convState}
                voicePaused={voicePausedRef.current}
                convMode={convMode}
                voiceTranscript={voiceTranscript}
              />
            </div>
          </div>

          <AnimatePresence>
            {mediaModalOpen && (
              <Modals
                isOpen={mediaModalOpen}
                onClose={() => setMediaModalOpen(false)}
                defaultTab={mediaModalTab}
                apiCall={apiCall}
                onAddMessage={addMessage}
              />
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
