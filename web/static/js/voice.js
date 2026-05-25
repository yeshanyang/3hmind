// ==================== TTS 预热 ====================
(function warmupSynth() {
  function pickVoice() {
    const voices = synth.getVoices();
    if (!voices.length) return null;
    let v = voices.find(v => v.lang === 'zh-CN' && v.localService) ||
            voices.find(v => v.lang.startsWith('zh-CN')) ||
            voices.find(v => v.lang.startsWith('zh')) ||
            voices[0];
    return v;
  }
  let voices = synth.getVoices();
  if (voices.length) {
    synthVoice = pickVoice();
  }
  synth.onvoiceschanged = () => {
    if (!synthVoice) synthVoice = pickVoice();
  };

  const warmUtterance = new SpeechSynthesisUtterance('');
  warmUtterance.volume = 0;
  warmUtterance.rate = 1.5;
  if (synthVoice) warmUtterance.voice = synthVoice;
  warmUtterance.onend = () => { synthReady = true; };
  warmUtterance.onerror = () => { synthReady = true; };
  setTimeout(() => { synthReady = true; }, 1500);
  synth.cancel();
  synth.speak(warmUtterance);
})();

// ==================== 语音在线模式（通过麦克风按钮切换） ====================
function toggleConversationMode() {
  const toggle = document.getElementById('convToggle');
  if (convMode) {
    // 关闭在线对话模式
    convMode = false;
    _voicePaused = false;
    _stopTypingWatch();
    stopListening();
    setConvState('idle');
    document.getElementById('chatInput').placeholder = '输入你想聊的话题...';
    resetFollowUpChain();
    toggle.classList.remove('on');
    addMessage('[在线对话模式已关闭] 回到手动输入模式。', 'system');
  } else {
    // 开启在线对话模式
    convMode = true;
    _voicePaused = false;
    toggle.classList.add('on');
    setConvState('idle');
    if (!micGated) {
      startListening();
    }
    addMessage('[在线对话模式已开启] 点击麦克风按钮开始语音对话。', 'system');
  }
}

// ==================== 打字监测（语音暂停后自动恢复） ====================
function _startTypingWatch() {
  _stopTypingWatch();
  const input = document.getElementById('chatInput');
  document.getElementById('micBtn').classList.add('paused');
  function onTyping() {
    if (_typingWatchTimer) clearTimeout(_typingWatchTimer);
    _typingWatchTimer = setTimeout(() => {
      _typingWatchTimer = null;
      if (convMode && _voicePaused && !micGated) {
        _voicePaused = false;
        input.removeEventListener('input', onTyping);
        input._typingWatchCleanup = null;
        document.getElementById('micBtn').classList.remove('paused');
        _stopTypingWatch();
        // 如果输入框有未发送的文字，保存后由语音覆盖
        if (document.getElementById('chatInput').value.trim()) {
          _savedTypedText = document.getElementById('chatInput').value;
        }
        startListening();
      }
    }, 5000);
  }
  input.addEventListener('input', onTyping);
  input._typingWatchCleanup = () => { input.removeEventListener('input', onTyping); };
}

function _stopTypingWatch() {
  const input = document.getElementById('chatInput');
  if (input && input._typingWatchCleanup) {
    input._typingWatchCleanup();
    input._typingWatchCleanup = null;
  }
  if (_typingWatchTimer) {
    clearTimeout(_typingWatchTimer);
    _typingWatchTimer = null;
  }
}

function forceStopTTS() {
  if (synth.speaking) {
    synth.cancel();
    ttsInterrupted = true;
  }
  _ttsResetQueue();
  micGated = false;
  document.querySelectorAll('.msg-speak-btn').forEach(b => {
    b.classList.remove('speaking');
    b.innerHTML = '&#128266;';
    b.dataset.muted = '0';
  });
  if (convState === 'speaking') setConvState('idle');
}

function toggleAutoSpeak() {
  autoSpeakEnabled = !autoSpeakEnabled;
  const toggle = document.getElementById('speakToggle');
  if (autoSpeakEnabled) {
    toggle.classList.add('on');
  } else {
    toggle.classList.remove('on');
    forceStopTTS();
  }
}

function toggleAutoAsk() {
  autoAskEnabled = !autoAskEnabled;
  const toggle = document.getElementById('askToggle');
  if (autoAskEnabled) {
    toggle.classList.add('on');
  } else {
    toggle.classList.remove('on');
  }
}

function stopAll() {
  convMode = false;
  _voicePaused = false;
  _stopTypingWatch();
  stopRecognition();
  cleanupMediaRecorder();
  voiceInputActive = false;
  voiceTranscript = '';
  voiceFinalText = '';
  // 保留用户手动输入的文字，不清空
  if (!_savedTypedText && !document.getElementById('chatInput').value.trim()) {
    document.getElementById('chatInput').value = '';
  }
  _savedTypedText = '';
  document.getElementById('chatInput').placeholder = '输入你想聊的话题...';
  document.getElementById('convToggle').classList.remove('on');
  forceStopTTS();
  if (inquiryActive) {
    stopInquiry();
  }
  lastUserMsg = '';
  lastAiResponse = '';
  waitingForInquiryAnswer = false;
  resetFollowUpChain();
  ttsInterrupted = false;
  _restartCount = 0;
  _hasSpoken = false;
  _exitingVoiceMode = false;
  setConvState('idle');
  document.getElementById('btnStopAll').style.display = 'none';
}

function setConvState(state) {
  convState = state;
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  const stopBtn = document.getElementById('btnStopAll');

  const stateConfig = {
    idle:    { cls: 'ok', status: '就绪' },
    listening: { cls: 'listening', status: '聆听中...' },
    processing: { cls: 'processing', status: '思考中...' },
    speaking: { cls: 'speaking', status: '回复中...' }
  };

  const cfg = stateConfig[state];
  dot.className = 'status-dot ' + cfg.cls;
  text.textContent = cfg.status;

  if (state !== 'idle' || inquiryActive) {
    stopBtn.style.display = 'inline-block';
  } else {
    stopBtn.style.display = 'none';
  }

  const micBtn = document.getElementById('micBtn');
  micBtn.classList.remove('active', 'conv-active', 'paused');
  if (state === 'listening') {
    micBtn.classList.add('active');
  }
  if (convMode) {
    micBtn.classList.add('conv-active');
  }
  if (_voicePaused) {
    micBtn.classList.add('paused');
  }
}

// ==================== 句尾/停止意图检测 ====================
function detectSentenceEnd(text) {
  if (!text || text.length < 3) return false;
  const t = text.trim();
  for (const pattern of SENTENCE_END_PATTERNS) {
    if (pattern.test(t)) return true;
  }
  return false;
}

function detectStopIntent(text) {
  const t = text.toLowerCase().replace(/\s+/g, '');
  return STOP_PHRASES.some(p => t.includes(p));
}

function detectVoiceEndPhrase(text) {
  if (!text || text.length < 3) return false;
  const t = text.replace(/\s+/g, '');
  return VOICE_INPUT_END_PHRASES.some(p => t.includes(p));
}

// ==================== 语音识别 (Web Speech API) ====================
function toggleMic() {
  if (_exitingVoiceMode) return;

  if (_useMediaRecorder) {
    if (convState === 'listening') {
      if (convMode) {
        // 在线对话模式中：丢弃录音数据，暂停并启动打字监测
        mediaChunks = [];
        _voicePaused = true;
        setConvState('idle');
      }
      stopMediaRecord();
      if (convMode) {
        document.getElementById('chatInput').placeholder = '打字中... (5秒无输入后自动恢复监听)';
        _startTypingWatch();
      } else {
        // 一次性录音：发送
        sendChat();
      }
    } else if (!micGated) {
      if (convMode) {
        _voicePaused = false;
        _stopTypingWatch();
      }
      startMediaRecord();
    }
    return;
  }

  if (convState === 'listening') {
    // 停止监听
    if (convMode) {
      // 在线对话模式中：暂停语音，启动打字监测自动恢复
      // 先改状态再 stopRecognition，防止 onend 中 restartListening 覆盖暂停
      _voicePaused = true;
      setConvState('idle');
      stopRecognition();
      document.getElementById('chatInput').placeholder = '打字中... (5秒无输入后自动恢复监听)';
      _startTypingWatch();
    } else {
      // 一次性语音：停止并让 onend 处理发送
      stopRecognition();
    }
  } else if (!micGated) {
    // 开始监听
    if (convMode) {
      _voicePaused = false;
      _stopTypingWatch();
    }
    startListening();
  }
}

function startListening(keepText = false) {
  if (_useMediaRecorder) { startMediaRecord(); return; }

  // 如果用户正在手动输入文字，不自动启动语音（但 typing watch 恢复/手动恢复除外）
  if (!voiceInputActive && !_voicePaused && !keepText) {
    const existingText = document.getElementById('chatInput').value.trim();
    if (existingText.length > 0) {
      return;
    }
  }
  // 清除暂停状态
  _voicePaused = false;
  _stopTypingWatch();

  stopRecognition();

  if (micGated) {
    let retries = 0;
    const maxRetries = 10;
    function pollMicGate() {
      if (!micGated && convMode && convState === 'idle') {
        startListening();
      } else if (retries < maxRetries && convMode) {
        retries++;
        setTimeout(pollMicGate, 200);
      }
    }
    setTimeout(pollMicGate, 200);
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    addMessage('[语音] 您的浏览器不支持语音识别。请使用 Chrome 或 Edge。', 'system');
    return;
  }

  if (synth.speaking) synth.cancel();

  // 保存用户手动输入的文字，语音结束后恢复
  if (!voiceInputActive) {
    _savedTypedText = document.getElementById('chatInput').value;
  }
  if (!keepText) {
    voiceTranscript = '';
  }
  silenceHandled = false;
  recognition = new SpeechRecognition();
  recognition.lang = 'zh-CN';
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    _networkErrCount = 0;
    if (!voiceInputActive && document.getElementById('chatInput').value.trim()) {
      _savedTypedText = document.getElementById('chatInput').value;
    }
    voiceInputActive = true;
    if (!keepText) {
      voiceFinalText = '';
      document.getElementById('chatInput').value = '';
    }
    setConvState('listening');
    document.getElementById('chatInput').placeholder = '正在聆听... (说出结束词自动发送)';
    resetSilenceTimer();
  };

  recognition.onresult = (event) => {
    _hasSpoken = true;
    _restartCount = 0;
    _networkErrCount = 0;
    _lastInputWasVoice = false;
    _silentCycles = 0;
    resetFollowUpChain();
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
      voiceTranscript += finalText;
    }
    const fullText = voiceTranscript + interimText;
    voiceFinalText = fullText;
    document.getElementById('chatInput').value = fullText;
    // 检测结束词 — 触发自动发送
    if (detectVoiceEndPhrase(voiceTranscript.trim())) {
      clearSilenceTimer();
      voiceInputActive = false;  // 先标记，防止 onend 重复发送
      stopRecognition();
      finishVoiceInput();
    }
  };

  recognition.onerror = (event) => {
    if (event.error === 'no-speech') {
      // no-speech 不算错误但需恢复手动输入的文字
      if (_savedTypedText) {
        document.getElementById('chatInput').value = _savedTypedText;
        _savedTypedText = '';
      }
      return;
    }
    if (event.error === 'aborted') { return; }
    clearSilenceTimer();
    voiceInputActive = false;
    // 恢复用户在语音启动前手动输入的文字
    if (_savedTypedText) {
      document.getElementById('chatInput').value = _savedTypedText;
      _savedTypedText = '';
    }
    stopRecognition();
    setConvState('idle');

    if (event.error === 'network' || event.error === 'service-not-allowed' || event.error === 'not-allowed') {
      _networkErrCount++;
      if (_networkErrCount <= 3) {
        const delay = Math.min(_networkErrCount * 2, 6) * 1000;
        if (convMode) {
          setTimeout(() => {
            if (convMode && convState === 'idle') startListening();
          }, delay);
        }
        return;
      }
      if (!_useMediaRecorder) {
        _useMediaRecorder = true;
        addMessage('[语音] 浏览器语音服务不可用，已切换为录音模式。点击麦克风开始/停止录音。', 'system');
        document.getElementById('micBtn').classList.add('record-mode');
        if (convMode) {
          document.getElementById('chatInput').placeholder = '点击麦克风录音...';
        }
      }
      _networkErrCount = 0;
      return;
    }

    _networkErrCount = 0;
    addMessage('[语音] 识别出错: ' + event.error, 'system');
  };

  recognition.onspeechend = () => {
    if (!silenceTimer && voiceTranscript.trim().length >= 2) {
      const isComplete = detectSentenceEnd(voiceTranscript.trim());
      const timeout = isComplete ? SILENCE_SHORT : SILENCE_LONG;
      startSilenceCountdown(timeout);
    }
  };

  recognition.onend = () => {
    if (convMode && convState === 'listening') {
      restartListening();
      return;
    }
    if (!convMode) {
      // 静音倒计时进行中说明浏览器提前结束了识别，自动重启继续聆听，保留已累积文本
      if (silenceTimer) {
        recognition = null;
        startListening(true);
        return;
      }
      const text = document.getElementById('chatInput').value.trim();
      stopRecognition();
      if (text && text.length > 2 && voiceInputActive) {
        voiceInputActive = false;
        sendChat();
      } else {
        voiceInputActive = false;
        if (_savedTypedText) {
          document.getElementById('chatInput').value = _savedTypedText;
          _savedTypedText = '';
        }
        document.getElementById('chatInput').placeholder = '输入你想聊的话题...';
        document.getElementById('micBtn').classList.remove('active', 'conv-active');
      }
    }
  };

  try {
    recognition.start();
    document.getElementById('micBtn').classList.add(convMode ? 'conv-active' : 'active');
  } catch(e) {
    addMessage('[语音] 启动失败，1.5s后重试: ' + e.message, 'system');
    setTimeout(() => {
      if (convMode && convState === 'listening') startListening();
    }, 1500);
  }
}

// ==================== MediaRecorder 录音模式 ====================
async function startMediaRecord() {
  // 如果用户正在手动输入文字，保存后由录音覆盖
  if (!voiceInputActive && document.getElementById('chatInput').value.trim()) {
    _savedTypedText = document.getElementById('chatInput').value;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({audio: true});
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus' : 'audio/webm';

    mediaRecorder = new MediaRecorder(stream, {mimeType});
    mediaChunks = [];
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) mediaChunks.push(e.data);
    };
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      if (!mediaChunks.length) {
        // 录音无数据，恢复手动输入的文字
        if (_savedTypedText) {
          document.getElementById('chatInput').value = _savedTypedText;
          _savedTypedText = '';
        }
        return;
      }

      const blob = new Blob(mediaChunks, {type: mimeType});
      mediaChunks = [];
      await sendAudioToSTT(blob);
    };

    mediaRecorder.start(250);
    voiceInputActive = true;
    voiceFinalText = '';
    setConvState('listening');
    document.getElementById('micBtn').classList.add('recording');
    document.getElementById('chatInput').value = '';
    document.getElementById('chatInput').placeholder = '正在录音... 点击麦克风停止';
    addMessage('[录音] 正在录音中...', 'system');
  } catch(e) {
    // 录音启动失败，恢复手动输入的文字
    if (_savedTypedText) {
      document.getElementById('chatInput').value = _savedTypedText;
      _savedTypedText = '';
    }
    addMessage('[录音] 无法启动麦克风: ' + e.message, 'system');
    _useMediaRecorder = false;
    document.getElementById('micBtn').classList.remove('record-mode');
  }
}

function stopMediaRecord() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    document.getElementById('micBtn').classList.remove('recording');
    document.getElementById('chatInput').placeholder = '识别中...';
  }
}

async function sendAudioToSTT(blob) {
  const formData = new FormData();
  formData.append('file', blob, 'recording.webm');

  try {
    const resp = await api('/api/stt', {method: 'POST', body: formData});
    const data = await resp.json();
    if (data.text && data.text.trim()) {
      voiceFinalText = data.text.trim();
      _lastInputWasVoice = true;
      finishVoiceInput();
      return;
    } else if (data.error) {
      addMessage('[语音] ' + data.error, 'system');
    } else {
      addMessage('[语音] 未识别到语音内容，请重试。', 'system');
    }
  } catch(e) {
    addMessage('[语音] 识别请求失败: ' + e.message, 'system');
  }

  voiceInputActive = false;
  // 恢复用户在录音前手动输入的文字
  if (_savedTypedText) {
    document.getElementById('chatInput').value = _savedTypedText;
    _savedTypedText = '';
  }
  document.getElementById('chatInput').placeholder = _useMediaRecorder
    ? '点击麦克风录音...' : '输入你想聊的话题...';
  setConvState('idle');

  if (convMode && convState === 'idle') {
    setTimeout(() => {
      if (convMode && convState === 'idle' && _useMediaRecorder) {
        startMediaRecord();
      }
    }, 1500);
  }
}

function cleanupMediaRecorder() {
  if (mediaRecorder) {
    if (mediaRecorder.state !== 'inactive') {
      mediaRecorder.onstop = null;
      mediaRecorder.stop();
    }
    mediaRecorder = null;
  }
  mediaChunks = [];
  document.getElementById('micBtn').classList.remove('recording', 'record-mode');
}

// ==================== 渐进重启 ====================
function restartListening() {
  if (_restartingListening) return;
  if (_voicePaused) return;  // 暂停中不自动重启
  _restartingListening = true;
  if (recognition) {
    const r = recognition;
    recognition = null;
    try { r.stop(); } catch(e) {}
  }
  clearSilenceTimer();

  if (!voiceTranscript.trim()) {
    voiceTranscript = '';
    silenceHandled = false;
  }

  _restartCount++;
  let delay;
  if (!_hasSpoken) {
    delay = 1000;
    _restartCount = 0;
  } else {
    const delayIdx = Math.min(_restartCount - 1, RESTART_DELAYS.length - 1);
    delay = RESTART_DELAYS[delayIdx] * 1000;
  }

  setTimeout(() => {
    _restartingListening = false;
    if (convMode && convState === 'listening' && !_voicePaused) startListening();
  }, delay);
}

// ==================== 静音检测 ====================
function resetSilenceTimer() {
  clearSilenceTimer();
  const fullText = (voiceTranscript + document.getElementById('chatInput').value.replace(voiceTranscript, '')).trim();
  const isComplete = detectSentenceEnd(fullText);
  const timeout = isComplete ? SILENCE_SHORT : SILENCE_LONG;
  startSilenceCountdown(timeout);
}

function startSilenceCountdown(timeout) {
  clearSilenceTimer();
  silenceHandled = false;
  silenceCountdown = timeout || SILENCE_LONG;
  updateListeningPlaceholder();

  countdownInterval = setInterval(() => {
    silenceCountdown--;
    updateListeningPlaceholder();
    if (silenceCountdown <= 0) {
      clearSilenceTimer();
      handleSilenceTimeout();
    }
  }, 1000);

  silenceTimer = setTimeout(() => {
    handleSilenceTimeout();
  }, (timeout || SILENCE_LONG) * 1000);
}

function clearSilenceTimer() {
  if (silenceTimer) { clearTimeout(silenceTimer); silenceTimer = null; }
  if (countdownInterval) { clearInterval(countdownInterval); countdownInterval = null; }
  silenceCountdown = 0;
}

function updateListeningPlaceholder() {
  const input = document.getElementById('chatInput');
  if (silenceCountdown > 0 && convState === 'listening') {
    if (silenceCountdown <= SILENCE_SHORT + 1) {
      input.placeholder = `语句结束，${silenceCountdown}秒后发送...`;
    } else {
      input.placeholder = `正在聆听... (${silenceCountdown}秒后自动结束)`;
    }
  } else if (convState === 'listening') {
    input.placeholder = '正在聆听... 请说话';
  }
}

function handleSilenceTimeout() {
  if (silenceHandled) return;
  silenceHandled = true;
  clearSilenceTimer();
  const accumulated = voiceTranscript.trim();

  if (convMode) {
    if (accumulated && accumulated.length >= 2) {
      if (detectStopIntent(accumulated)) {
        stopRecognition();
        addMessage('[语音] ' + accumulated, 'user');
        addMessage('[对话结束] 检测到停止意图。', 'system');
        toggleConversationMode();
        return;
      }
      voiceInputActive = false;
      stopRecognition();
      _hasSpoken = false;
      _lastInputWasVoice = true;
      finishVoiceInput();
    } else {
      if (convState === 'listening') {
        stopRecognition();
        _hasSpoken = false;
        silenceHandled = false;
        _silentCycles++;
        if (_silentCycles >= 3) {
          _silentCycles = 0;
          setConvState('idle');
          if (_followUpCount < MAX_FOLLOW_UPS && autoAskEnabled) {
            tryAskFollowUp();
          }
        } else {
          setTimeout(() => {
            if (convMode && convState === 'idle') startListening();
          }, 300);
        }
      }
    }
  } else if (accumulated && accumulated.length >= 2) {
    voiceInputActive = false;
    stopRecognition();
    finishVoiceInput();
  } else if (convState === 'listening') {
    voiceInputActive = false;
    stopRecognition();
    document.getElementById('chatInput').placeholder = '输入你想聊的话题...';
    setConvState('idle');
  }
}

// ==================== 停止与清理 ====================
function stopRecognition() {
  if (recognition) {
    try { recognition.stop(); } catch(e) {}
    recognition = null;
  }
  clearSilenceTimer();
  const micBtn = document.getElementById('micBtn');
  micBtn.classList.remove('active');
  if (!convMode) {
    micBtn.classList.remove('conv-active');
  }
}

function stopListening() {
  stopRecognition();
  cleanupMediaRecorder();
  _useMediaRecorder = false;
  _networkErrCount = 0;
  voiceInputActive = false;
  voiceFinalText = '';
  // 恢复用户在语音启动前手动输入的文字
  if (_savedTypedText) {
    document.getElementById('chatInput').value = _savedTypedText;
    _savedTypedText = '';
  }
  setConvState('idle');
  document.getElementById('chatInput').placeholder = convMode ? '正在聆听... (点击麦克风继续)' : '输入你想聊的话题...';
}

// ==================== 语音输入完成 & 取消 ====================
async function finishVoiceInput() {
  voiceInputActive = false;
  _savedTypedText = '';  // 语音输入已确认，丢弃保存的手动输入文字
  const rawText = (voiceFinalText || voiceTranscript || '').trim();

  if (!rawText || rawText.length < 2) {
    setConvState(convMode ? 'idle' : 'idle');
    document.getElementById('chatInput').placeholder = convMode ? '正在聆听... (点击麦克风继续)' : '输入你想聊的话题...';
    if (convMode && convState === 'idle') { setTimeout(() => { if (convMode && convState === 'idle') startListening(); }, 500); }
    return;
  }

  setConvState('processing');
  document.getElementById('chatInput').placeholder = '正在优化语音文本...';

  try {
    const resp = await api('/api/voice/refine', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: rawText})
    });
    const data = await resp.json();
    const refinedText = data.refined || rawText;
    document.getElementById('chatInput').value = refinedText;
    voiceTranscript = '';
    voiceFinalText = '';
    _lastInputWasVoice = true;
    if (convMode) {
      sendStreamChat(refinedText, 'voice');
    } else {
      sendChat();
    }
  } catch(e) {
    document.getElementById('chatInput').value = rawText;
    voiceTranscript = '';
    voiceFinalText = '';
    _lastInputWasVoice = true;
    if (convMode) {
      sendStreamChat(rawText, 'voice');
    } else {
      sendChat();
    }
  }
}

function cancelVoiceInput() {
  voiceInputActive = false;
  voiceTranscript = '';
  voiceFinalText = '';
  silenceHandled = true;
  clearSilenceTimer();
  stopRecognition();
  // 恢复用户在语音启动前手动输入的文字
  if (_savedTypedText) {
    document.getElementById('chatInput').value = _savedTypedText;
    _savedTypedText = '';
  } else {
    document.getElementById('chatInput').value = '';
  }
  document.getElementById('chatInput').placeholder = convMode ? '点击麦克风开始说话...' : '输入你想聊的话题...';
  setConvState(convMode ? 'idle' : 'idle');
  document.getElementById('micBtn').classList.remove('active', 'conv-active');
  addMessage('[语音] 语音输入已取消。', 'system');
  if (convMode) {
    setTimeout(() => { if (convMode && convState === 'idle') startListening(); }, 500);
  }
}

// ==================== TTS 通用朗读 ====================
function speakText(text, msgDiv = null) {
  return new Promise((resolve) => {
    if (!autoSpeakEnabled) return resolve();
    if (!text) return resolve();
    if (synth.speaking) synth.cancel();

    micGated = true;
    stopRecognition();

    const cleanText = text.replace(/[【】\[\]=#\-\*～\n]+/g, ' ').substring(0, 2000);
    const utterance = new SpeechSynthesisUtterance(cleanText);
    if (synthVoice) utterance.voice = synthVoice;
    utterance.lang = 'zh-CN';
    utterance.rate = 1.5;
    utterance.pitch = 1.0;

    const speakBtn = msgDiv ? msgDiv.querySelector('.msg-speak-btn') : null;
    if (speakBtn) {
      speakBtn.classList.add('speaking');
      speakBtn.innerHTML = '&#128266;';
      speakBtn.dataset.muted = '0';
    }

    utterance.onend = () => {
      if (speakBtn) speakBtn.classList.remove('speaking');
      setTimeout(() => { micGated = false; }, 200);
      resolve();
    };
    utterance.onerror = () => {
      if (speakBtn) speakBtn.classList.remove('speaking');
      setTimeout(() => { micGated = false; }, 200);
      resolve();
    };

    ttsInterrupted = false;
    synth.resume();
    synth.speak(utterance);
  });
}

function speakMessage(msgDiv, text) {
  const btn = msgDiv.querySelector('.msg-speak-btn');
  if (synth.speaking) {
    if (btn) {
      btn.classList.remove('speaking');
      btn.innerHTML = '&#128264;';
      btn.dataset.muted = '1';
    }
    forceStopTTS();
    return;
  }
  if (btn && btn.dataset.muted === '1') {
    btn.dataset.muted = '0';
    btn.innerHTML = '&#128266;';
  }
  speakText(text, msgDiv);
}

// ==================== 追问链 ====================
function scheduleNextFollowUp() {
  clearFollowUpTimer();
  if (_followUpCount >= MAX_FOLLOW_UPS) return;
  if (!autoAskEnabled) return;

  // 检查用户是否正在输入 — 如果有文字未发送，延后追问
  const input = document.getElementById('chatInput');
  const hasPendingText = input && input.value.trim().length > 0;
  if (hasPendingText || (convMode && convState === 'listening')) {
    // 用户正在输入或语音聆听中，延后 3 秒重新检查
    followUpTimer = setTimeout(() => {
      followUpTimer = null;
      scheduleNextFollowUp();
    }, 3000);
    return;
  }

  const delay = (FOLLOW_UP_DELAYS[_followUpCount] || 10) * 1000;
  followUpTimer = setTimeout(async () => {
    followUpTimer = null;
    await tryAskFollowUp();
  }, delay);
}

function _isUserActive() {
  const input = document.getElementById('chatInput');
  if (input && input.value.trim().length > 0) return true;
  if (typeof voiceInputActive !== 'undefined' && voiceInputActive) return true;
  if (convMode && convState === 'listening') return true;
  if (convState === 'speaking') return true;
  return false;
}

function speakAndResume(msgDiv, text) {
  return speakText(text, msgDiv).then(async () => {
    if (!convMode) return;

    setConvState('idle');
    startListening();

    if (_lastInputWasVoice) {
      _lastInputWasVoice = false;
      return;
    }
    scheduleNextFollowUp();
  });
}

function clearFollowUpTimer() {
  if (followUpTimer) {
    clearTimeout(followUpTimer);
    followUpTimer = null;
  }
}

function resetFollowUpChain() {
  clearFollowUpTimer();
  _followUpCount = 0;
}
