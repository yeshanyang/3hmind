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

// ==================== 对话模式开关 ====================
function toggleConversationMode() {
  convMode = !convMode;
  const toggle = document.getElementById('convToggle');

  if (convMode) {
    toggle.classList.add('on');
    setConvState('idle');
    addMessage('[在线对话模式已开启] 点击麦克风按钮开始语音对话，说完后自动回复、自动朗读、自动继续聆听。', 'system');
  } else {
    toggle.classList.remove('on');
    stopListening();
    setConvState('idle');
    if (inquiryActive) {
      stopInquiry();
    }
    addMessage('[在线对话模式已关闭] 回到手动输入模式。', 'system');
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
  stopRecognition();
  cleanupMediaRecorder();
  document.getElementById('chatInput').value = '';
  document.getElementById('chatInput').placeholder = '输入你想聊的话题...';
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
  setConvState('idle');
  document.getElementById('btnStopAll').style.display = 'none';
}

function setConvState(state) {
  convState = state;
  const bar = document.getElementById('convBar');
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  const stopBtn = document.getElementById('btnStopAll');

  bar.className = 'conv-bar ' + state + (convMode ? ' show' : state === 'idle' ? ' show' : '');

  const stateConfig = {
    idle:    { msg: convMode ? '等待说话... (点击麦克风开始)' : '在线对话已关闭，点击右上角开启', cls: 'ok', status: '就绪' },
    listening: { msg: '正在聆听... 请说话 (仅录入外部声音)', cls: 'listening', status: '聆听中...' },
    processing: { msg: '正在思考... 请稍候', cls: 'processing', status: '思考中...' },
    speaking: { msg: '正在回复... 麦克风已静音 (不录入系统声音)', cls: 'speaking', status: '回复中...' }
  };

  const cfg = stateConfig[state];
  dot.className = 'status-dot ' + cfg.cls;
  text.textContent = cfg.status;
  bar.textContent = cfg.msg;

  if (state !== 'idle' || inquiryActive) {
    stopBtn.style.display = 'inline-block';
  } else {
    stopBtn.style.display = 'none';
  }

  const micBtn = document.getElementById('micBtn');
  micBtn.classList.remove('active', 'conv-active');
  if (state === 'listening') {
    micBtn.classList.add('active');
    if (convMode) micBtn.classList.add('conv-active');
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

// ==================== 语音识别 (Web Speech API) ====================
function toggleMic() {
  if (_useMediaRecorder) {
    if (convState === 'listening') {
      stopMediaRecord();
    } else if (!micGated) {
      startMediaRecord();
    }
    return;
  }
  if (convState === 'listening') {
    stopListening();
  } else if (!micGated) {
    startListening();
  }
}

function startListening() {
  if (_useMediaRecorder) { startMediaRecord(); return; }
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

  voiceTranscript = '';
  silenceHandled = false;
  recognition = new SpeechRecognition();
  recognition.lang = 'zh-CN';
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    _networkErrCount = 0;
    setConvState('listening');
    document.getElementById('chatInput').value = '';
    document.getElementById('chatInput').placeholder = '正在聆听... (请开始说话)';
    resetSilenceTimer();
  };

  recognition.onresult = (event) => {
    _hasSpoken = true;
    _restartCount = 0;
    _networkErrCount = 0;
    _lastInputWasVoice = false;
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
    document.getElementById('chatInput').value = voiceTranscript + interimText;
  };

  recognition.onerror = (event) => {
    if (event.error === 'no-speech') { return; }
    if (event.error === 'aborted') { return; }
    clearSilenceTimer();
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
      if (recognition._ending) return;
      recognition._ending = true;
      const text = document.getElementById('chatInput').value.trim();
      stopRecognition();
      if (text && text.length > 2) {
        sendChat();
      } else {
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
      if (!mediaChunks.length) return;

      const blob = new Blob(mediaChunks, {type: mimeType});
      mediaChunks = [];
      await sendAudioToSTT(blob);
    };

    mediaRecorder.start(250);
    setConvState('listening');
    document.getElementById('micBtn').classList.add('recording');
    document.getElementById('chatInput').value = '';
    document.getElementById('chatInput').placeholder = '正在录音... 点击麦克风停止';
    addMessage('[录音] 正在录音中...', 'system');
  } catch(e) {
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
      const text = data.text.trim();
      document.getElementById('chatInput').value = text;
      addMessage('[语音] ' + text, 'user');
      if (convMode) {
        _lastInputWasVoice = true;
        sendStreamChat(text, 'voice');
      }
    } else if (data.error) {
      addMessage('[语音] ' + data.error, 'system');
    } else {
      addMessage('[语音] 未识别到语音内容，请重试。', 'system');
    }
  } catch(e) {
    addMessage('[语音] 识别请求失败: ' + e.message, 'system');
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
    if (convMode && convState === 'listening') startListening();
  }, delay);
}

// ==================== 静音检测 ====================
function resetSilenceTimer() {
  clearSilenceTimer();
  if (convMode) {
    const fullText = (voiceTranscript + document.getElementById('chatInput').value.replace(voiceTranscript, '')).trim();
    const isComplete = detectSentenceEnd(fullText);
    const timeout = isComplete ? SILENCE_SHORT : SILENCE_LONG;
    startSilenceCountdown(timeout);
  }
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
        addMessage('[对话结束] 检测到停止意图，已关闭在线对话。随时可以重新开启。', 'system');
        toggleConversationMode();
        return;
      }
      stopRecognition();
      _hasSpoken = false;
      _lastInputWasVoice = true;
      sendStreamChat(accumulated, 'voice');
    } else {
      if (convState === 'listening') {
        stopRecognition();
        _hasSpoken = false;
        silenceHandled = false;
        setTimeout(() => {
          if (convMode && convState === 'idle') startListening();
        }, 300);
      }
    }
  }
}

// ==================== 停止与清理 ====================
function stopRecognition() {
  if (recognition) {
    try { recognition.stop(); } catch(e) {}
    recognition = null;
  }
  clearSilenceTimer();
  document.getElementById('micBtn').classList.remove('active', 'conv-active');
}

function stopListening() {
  stopRecognition();
  cleanupMediaRecorder();
  _useMediaRecorder = false;
  _networkErrCount = 0;
  setConvState('idle');
  document.getElementById('chatInput').placeholder = convMode ? '点击麦克风开始对话...' : '输入你想聊的话题...';
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
  if (_followUpCount >= MAX_FOLLOW_UPS) { return; }
  if (_lastInputWasVoice) {
    _lastInputWasVoice = false;
    return;
  }
  const delay = (FOLLOW_UP_DELAYS[_followUpCount] || 40) * 1000;
  followUpTimer = setTimeout(async () => {
    followUpTimer = null;
    if (!convMode) return;
    if (convState === 'listening' && !voiceTranscript.trim()) {
      await tryAskFollowUp();
    }
  }, delay);
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
    if (autoAskEnabled && lastUserMsg && lastAiResponse && _followUpCount === 0) {
      clearFollowUpTimer();
      const txtLen = (text || '').length;
      let delay;
      if (!autoSpeakEnabled || ttsInterrupted) {
        delay = Math.min(Math.max(txtLen * 0.03 + 5, 10), 35);
      } else {
        delay = Math.min(Math.max(txtLen * 0.015 + 5, 8), 25);
      }
      followUpTimer = setTimeout(async () => {
        followUpTimer = null;
        if (!convMode) return;
        if (convState === 'listening' && !voiceTranscript.trim()) {
          await tryAskFollowUp();
        }
      }, delay * 1000);
    }
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
