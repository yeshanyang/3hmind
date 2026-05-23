// ==================== 流式 TTS 辅助 ====================
function _ttsSliceSentences(text) {
  const newText = text.slice(_ttsSpokenLen);
  const parts = [];
  let lastEnd = 0;
  for (let i = 0; i < newText.length; i++) {
    if (_SENTENCE_RE.test(newText[i])) {
      parts.push(newText.slice(lastEnd, i + 1));
      lastEnd = i + 1;
    }
  }
  if (lastEnd > 0) _ttsSpokenLen += lastEnd;
  return parts;
}

async function _ttsFlushQueue() {
  if (_ttsBusy) return;
  while (_ttsQueue.length) {
    const sentence = _ttsQueue.shift();
    _ttsBusy = true;
    await _ttsSpeakOne(sentence);
    _ttsBusy = false;
  }
}

function _ttsSpeakOne(text) {
  return new Promise((resolve) => {
    if (!autoSpeakEnabled) return resolve();
    const clean = text.replace(/[【】\[\]=#\-\*～\n]+/g, ' ').trim();
    if (!clean) return resolve();
    const u = new SpeechSynthesisUtterance(clean);
    if (synthVoice) u.voice = synthVoice;
    u.lang = 'zh-CN';
    u.rate = 1.5;
    u.pitch = 1.0;
    u.onend = () => resolve();
    u.onerror = () => resolve();
    synth.resume();
    synth.speak(u);
  });
}

function _ttsResetQueue() {
  _ttsQueue = [];
  _ttsBusy = false;
  _ttsSpokenLen = 0;
  _ttsActive = false;
}

// ==================== SSE 流式对话 ====================
async function sendStreamChat(msg, contextType) {
  if (sendLocked) return;
  sendLocked = true;

  if (inquiryActive && waitingForInquiryAnswer) {
    sendLocked = false;
    return sendInquiryAnswer(msg);
  }

  addMessage(msg, 'user');
  document.getElementById('chatInput').value = '';

  if (detectStopIntent(msg)) {
    addMessage('[对话结束] 检测到停止意图，已关闭在线对话。随时可以重新开启。', 'system');
    if (convMode) toggleConversationMode();
    sendLocked = false;
    return;
  }

  setConvState('processing');

  const msgDiv = document.createElement('div');
  msgDiv.className = 'message agent streaming';
  msgDiv.id = 'streamMsg';
  document.getElementById('chatArea').appendChild(msgDiv);

  _ttsResetQueue();
  _ttsActive = true;

  let fullText = '';
  let buffer = '';

  try {
    const resp = await api('/api/chat/stream', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg, context_type: contextType || 'voice'})
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, {stream: true});
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) {
              fullText += data.token;
              msgDiv.textContent = fullText;
              document.getElementById('chatArea').scrollTop = document.getElementById('chatArea').scrollHeight;

              const newSentences = _ttsSliceSentences(fullText);
              if (newSentences.length && !_ttsBusy && _ttsQueue.length === 0) {
                if (autoSpeakEnabled) {
                  micGated = true;
                  stopRecognition();
                  setConvState('speaking');
                }
              }
              for (const s of newSentences) {
                _ttsQueue.push(s);
              }
              _ttsFlushQueue();
            }
            if (data.done) {
              msgDiv.classList.remove('streaming');
            }
            if (data.error) {
              msgDiv.textContent = '错误: ' + data.error;
              msgDiv.classList.remove('streaming');
            }
          } catch(e) {}
        }
      }
    }
  } catch(e) {
    msgDiv.textContent = '请求失败: ' + e.message;
    msgDiv.classList.remove('streaming');
  }

  const remaining = fullText.slice(_ttsSpokenLen).trim();
  if (remaining) {
    if (!_ttsBusy && _ttsQueue.length === 0 && autoSpeakEnabled) {
      micGated = true;
      stopRecognition();
      setConvState('speaking');
    }
    _ttsQueue.push(remaining);
    _ttsFlushQueue();
  }

  while (_ttsBusy || _ttsQueue.length) {
    await new Promise(r => setTimeout(r, 80));
  }

  _ttsActive = false;
  setTimeout(() => { micGated = false; }, 200);

  const finalText = msgDiv.textContent;
  if (finalText && finalText.length > 20 && !finalText.startsWith('错误') && !finalText.startsWith('请求失败')) {
    const btn = document.createElement('button');
    btn.className = 'msg-speak-btn';
    btn.innerHTML = '&#128266;';
    btn.title = '朗读';
    btn.onclick = (e) => { e.stopPropagation(); speakMessage(msgDiv, finalText); };
    msgDiv.appendChild(btn);
  }

  msgDiv.removeAttribute('id');

  checkProfileStatus();
  loadGoals();
  saveChatHistory();

  lastUserMsg = msg;
  lastAiResponse = finalText;

  if (finalText && !finalText.startsWith('错误') && !finalText.startsWith('请求失败')) {
    if (convMode) {
      startListening();
    }
    scheduleNextFollowUp();
  }
  setConvState(convMode ? 'idle' : 'idle');
  sendLocked = false;
}

// ==================== 文本对话 ====================
async function sendChat() {
  if (sendLocked) return;
  sendLocked = true;
  _lastInputWasVoice = false;

  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg) { sendLocked = false; return; }

  if (detectStopIntent(msg)) {
    addMessage(msg, 'user');
    input.value = '';
    addMessage('[对话结束] 检测到停止意图，已关闭在线对话。随时可以重新开启。', 'system');
    if (convMode) toggleConversationMode();
    sendLocked = false;
    return;
  }

  if (inquiryActive && waitingForInquiryAnswer) {
    sendLocked = false;
    return sendInquiryAnswer(msg);
  }

  addMessage(msg, 'user');
  input.value = '';
  showTyping();

  try {
    const resp = await api('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg, context_type: 'text'})
    });
    const data = await resp.json();
    removeTyping();
    const responseText = data.analysis || '无响应';
    const msgDiv = addMessage(responseText, 'agent', true);
    checkProfileStatus();
    loadGoals();
    saveChatHistory();

    lastUserMsg = msg;
    lastAiResponse = responseText;

    if (responseText && responseText.length > 5 && !responseText.startsWith('错误')) {
      setConvState('speaking');
      scheduleNextFollowUp();
      if (convMode) {
        speakAndResume(msgDiv, responseText).then(() => { sendLocked = false; });
        return;
      } else {
        speakText(responseText, msgDiv).then(() => {
          setConvState('idle');
          sendLocked = false;
        });
        return;
      }
    }
    sendLocked = false;
  } catch(e) {
    removeTyping();
    addMessage('请求失败: ' + e.message, 'system');
    sendLocked = false;
  }
}

async function sendAction(url) {
  showTyping();
  try {
    const resp = await api(url, {method: 'POST'});
    const data = await resp.json();
    removeTyping();
    const content = data.result || data.reflection || data.nudge || JSON.stringify(data);
    const msgDiv = addMessage(content, 'agent', true);
    saveChatHistory();
    loadGoals();
    if (content && content.length > 10) {
      speakText(content, msgDiv);
    }
  } catch(e) {
    removeTyping();
    addMessage('请求失败: ' + e.message, 'system');
  }
}

async function sendPlan() {
  showTyping();
  try {
    const resp = await api('/api/plan', {method: 'POST'});
    const data = await resp.json();
    removeTyping();
    const content = data.result || '无响应';
    const msgDiv = addMessage(content, 'agent', true);
    saveChatHistory();
    loadGoals();
    if (content && content.length > 10) {
      speakText(content, msgDiv);
    }
  } catch(e) {
    removeTyping();
    addMessage('请求失败: ' + e.message, 'system');
  }
}

async function loadDashboard() {
  showTyping();
  try {
    const resp = await api('/api/dashboard');
    const data = await resp.json();
    removeTyping();
    addMessage(data.result, 'agent');
    saveChatHistory();
    loadGoals();
  } catch(e) {
    removeTyping();
    addMessage('请求失败: ' + e.message, 'system');
  }
}

// ==================== AI 主动追问 ====================
async function tryAskFollowUp() {
  if (_followUpCount >= MAX_FOLLOW_UPS) return;
  if (!autoAskEnabled) return;

  // 追问前再次确认用户不在输入中 — 避免打断用户
  if (typeof _isUserActive === 'function' && _isUserActive()) {
    // 用户正在活动，延后 3 秒重新检查
    scheduleNextFollowUp();
    return;
  }

  _followUpCount++;

  try {
    const resp = await api('/api/proactive/question', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        last_user_msg: lastUserMsg,
        last_ai_response: lastAiResponse
      })
    });
    const data = await resp.json();
    if (!data.question) { scheduleNextFollowUp(); return; }

    // API 返回后再次确认用户状态
    if (typeof _isUserActive === 'function' && _isUserActive()) {
      _followUpCount--;
      scheduleNextFollowUp();
      return;
    }

    const askDiv = document.createElement('div');
    askDiv.className = 'message agent';
    askDiv.textContent = `[追问 ${_followUpCount}/${MAX_FOLLOW_UPS}] ` + data.question;
    askDiv.style.borderColor = '#a855f7';
    document.getElementById('chatArea').appendChild(askDiv);
    document.getElementById('chatArea').scrollTop = document.getElementById('chatArea').scrollHeight;
    saveChatHistory();

    const cleanQ = data.question.replace(/[【】\[\]=#\-\*～\n]+/g, ' ').substring(0, 500);
    await speakText(cleanQ, askDiv);

    if (convMode) {
      setConvState('idle');
      startListening();
    }

    scheduleNextFollowUp();
  } catch(e) {
    scheduleNextFollowUp();
  }
}

// ==================== 深度对话 (Inquiry Session) ====================
async function startInquiry() {
  const topicInput = document.getElementById('inquiryTopicInput');
  const topic = topicInput.value.trim();

  showTyping();
  try {
    const resp = await api('/api/inquiry/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({topic})
    });
    const data = await resp.json();
    removeTyping();

    if (!data.questions || data.questions.length === 0) {
      addMessage('[深度对话] 生成问题链失败，请重试。', 'system');
      return;
    }

    inquiryActive = true;
    inquiryQuestions = data.questions;
    inquiryIndex = 0;
    inquiryTopic = data.topic;
    waitingForInquiryAnswer = false;

    updateInquiryPanel();
    document.getElementById('inquiryPanel').classList.add('show');
    document.getElementById('btnInquiryStart').style.display = 'none';
    document.getElementById('btnInquiryStop').style.display = 'block';
    document.getElementById('inquiryTopicInput').style.display = 'none';

    addMessage(`[深度对话] 开始「${data.topic}」— 共 ${data.total} 个问题`, 'system');

    const firstQ = data.questions[0].text;
    const qDiv = document.createElement('div');
    qDiv.className = 'message agent';
    qDiv.textContent = firstQ;
    qDiv.style.borderColor = '#a855f7';
    document.getElementById('chatArea').appendChild(qDiv);
    document.getElementById('chatArea').scrollTop = document.getElementById('chatArea').scrollHeight;

    if (synth.speaking) synth.cancel();
    const cleanQ = firstQ.replace(/[【】\[\]=#\-\*～\n]+/g, ' ').substring(0, 500);
    const utterance = new SpeechSynthesisUtterance(cleanQ);
    if (synthVoice) utterance.voice = synthVoice;
    utterance.lang = 'zh-CN'; utterance.rate = 1.5; utterance.pitch = 1.0;
    utterance.onend = () => {
      waitingForInquiryAnswer = true;
      if (convMode) {
        setConvState('idle');
        setTimeout(() => { if (convMode && convState === 'idle') startListening(); }, 300);
      }
    };
    utterance.onerror = () => {
      waitingForInquiryAnswer = true;
      if (convMode) {
        setConvState('idle');
        setTimeout(() => { if (convMode && convState === 'idle') startListening(); }, 300);
      }
    };
    synth.resume();
    synth.speak(utterance);

  } catch(e) {
    removeTyping();
    addMessage('[深度对话] 启动失败: ' + e.message, 'system');
  }
}

async function sendInquiryAnswer(answer) {
  waitingForInquiryAnswer = false;
  addMessage(answer, 'user');
  document.getElementById('chatInput').value = '';
  setConvState('processing');

  try {
    const resp = await api('/api/inquiry/next', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({answer})
    });
    const data = await resp.json();

    if (data.done) {
      inquiryActive = false;
      waitingForInquiryAnswer = false;
      updateInquiryPanel();
      resetInquiryPanel();

      const summary = data.summary || '对话完成';
      addMessage(summary, 'agent', true);
      saveChatHistory();
      loadGoals();

      if (synth.speaking) synth.cancel();
      const cleanS = summary.replace(/[【】\[\]=#\-\*～\n]+/g, ' ').substring(0, 1000);
      const sUtterance = new SpeechSynthesisUtterance(cleanS);
      if (synthVoice) sUtterance.voice = synthVoice;
      sUtterance.lang = 'zh-CN'; sUtterance.rate = 1.5; sUtterance.pitch = 1.0;
      sUtterance.onend = () => {
        if (convMode) {
          setConvState('idle');
          setTimeout(() => { if (convMode && convState === 'idle') startListening(); }, 500);
        }
      };
      synth.resume();
      synth.speak(sUtterance);
      setConvState('speaking');
      return;
    }

    inquiryIndex = data.index;
    updateInquiryPanel();
    refreshInquiryInsights();

    let displayText = '';
    if (data.acknowledgment) {
      displayText = data.acknowledgment + '\n\n' + data.question;
    } else {
      displayText = data.question;
    }
    const nextDiv = document.createElement('div');
    nextDiv.className = 'message agent';
    nextDiv.textContent = displayText;
    nextDiv.style.borderColor = '#a855f7';
    document.getElementById('chatArea').appendChild(nextDiv);
    document.getElementById('chatArea').scrollTop = document.getElementById('chatArea').scrollHeight;
    saveChatHistory();

    if (synth.speaking) synth.cancel();
    const speechText = (data.acknowledgment ? data.acknowledgment + '。' : '') + data.question;
    const cleanT = speechText.replace(/[【】\[\]=#\-\*～\n]+/g, ' ').substring(0, 1000);
    const utterance = new SpeechSynthesisUtterance(cleanT);
    if (synthVoice) utterance.voice = synthVoice;
    utterance.lang = 'zh-CN'; utterance.rate = 1.5; utterance.pitch = 1.0;
    utterance.onend = () => {
      waitingForInquiryAnswer = true;
      if (convMode) {
        setConvState('idle');
        setTimeout(() => { if (convMode && convState === 'idle') startListening(); }, 300);
      }
    };
    utterance.onerror = () => {
      waitingForInquiryAnswer = true;
      if (convMode) {
        setConvState('idle');
        setTimeout(() => { if (convMode && convState === 'idle') startListening(); }, 300);
      }
    };
    synth.resume();
    synth.speak(utterance);
    setConvState('speaking');

  } catch(e) {
    addMessage('[深度对话] 请求失败: ' + e.message, 'system');
    waitingForInquiryAnswer = true;
    if (convMode) setConvState('idle');
  }
}

async function refreshInquiryInsights() {
  try {
    const resp = await api('/api/inquiry/status');
    const data = await resp.json();
    if (data.active && data.insights_count > 0) {
      document.getElementById('inquiryInsights').innerHTML =
        `<div style="color:#f59e0b;">[已收集 ${data.insights_count} 条洞察]</div>`;
    }
  } catch(e) {}
}

async function stopInquiry() {
  try {
    const resp = await api('/api/inquiry/stop', {method: 'POST'});
    const data = await resp.json();
    if (data.summary) {
      addMessage('[对话总结] ' + data.summary, 'agent', true);
      saveChatHistory();
      loadGoals();
    }
  } catch(e) {}
  inquiryActive = false;
  waitingForInquiryAnswer = false;
  resetInquiryPanel();
  if (convMode) setConvState('idle');
}

function updateInquiryPanel() {
  const list = document.getElementById('inquiryList');
  const progress = document.getElementById('inquiryProgress');
  const bar = document.getElementById('inquiryProgressBar');
  const topic = document.getElementById('inquiryTopic');

  topic.textContent = inquiryTopic || '深度对话';

  const completed = inquiryQuestions.filter(q => q.asked).length;
  progress.textContent = `${inquiryIndex + 1} / ${inquiryQuestions.length}`;
  bar.style.width = Math.round((inquiryIndex) / inquiryQuestions.length * 100) + '%';

  list.innerHTML = inquiryQuestions.map((q, i) => {
    let cls = '';
    if (q.asked) cls = 'done';
    else if (i === inquiryIndex && inquiryActive) cls = 'current';
    const icon = q.asked ? '&#10003;' : (i + 1);
    const summary = q.answer_summary ? `<br><span style="color:#94a3b8;font-size:10px;">答: ${q.answer_summary.substring(0, 50)}...</span>` : '';
    return `<li class="${cls}"><span class="q-num">${icon}</span><span>${q.text}${summary}</span></li>`;
  }).join('');
}

function resetInquiryPanel() {
  inquiryActive = false;
  inquiryQuestions = [];
  inquiryIndex = 0;
  inquiryTopic = '';
  waitingForInquiryAnswer = false;
  document.getElementById('inquiryPanel').classList.remove('show');
  document.getElementById('btnInquiryStart').style.display = 'block';
  document.getElementById('btnInquiryStop').style.display = 'none';
  document.getElementById('inquiryTopicInput').style.display = 'block';
  document.getElementById('inquiryList').innerHTML = '';
  document.getElementById('inquiryProgress').textContent = '';
  document.getElementById('inquiryProgressBar').style.width = '0%';
  document.getElementById('inquiryInsights').innerHTML = '';
}

// ==================== 对话历史持久化 ====================
function saveChatHistory() {
  const area = document.getElementById('chatArea');
  if (area) {
    try { sessionStorage.setItem('3hmind_chat', area.innerHTML); } catch(e) {}
  }
}

function restoreChatHistory() {
  try {
    const saved = sessionStorage.getItem('3hmind_chat');
    if (saved) {
      document.getElementById('chatArea').innerHTML = saved;
    }
  } catch(e) {}
}
