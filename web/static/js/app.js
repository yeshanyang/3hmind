// ==================== 自主消息轮询 ====================
function startPolling() {
  polling = setInterval(async () => {
    if (convMode && convState !== 'idle') return;
    try {
      const resp = await api('/api/poll');
      const data = await resp.json();
      if (data.reflection) addMessage('[自主复盘]\n' + data.reflection, 'agent', true);
      if (data.nudge) addMessage('[自主提醒]\n' + data.nudge, 'agent', true);
      if (data.reflection || data.nudge) {
        document.getElementById('statusDot').className = 'status-dot warn';
        document.getElementById('statusText').textContent = '有新消息';
        setTimeout(() => {
          if (convState === 'idle') {
            document.getElementById('statusDot').className = 'status-dot ok';
            document.getElementById('statusText').textContent = '就绪';
          }
        }, 5000);
      }
    } catch(e) {}
  }, 15000);
}

async function initApp() {
  startPolling();
  checkProfileStatus();
  try {
    const resp = await api('/api/profile/status');
    const data = await resp.json();
    if (!data.complete) {
      const discResp = await api('/api/profile/discover');
      const discData = await discResp.json();
      if (discData.question) {
        addMessage('[画像探索] ' + discData.question, 'agent', true);
      }
    }
  } catch(e) {}

  setTimeout(autoStart, 1200);
}

function autoStart() {
  if (!convMode) {
    convMode = true;
    document.getElementById('convToggle').classList.add('on');
  }
  if (!autoSpeakEnabled) {
    document.getElementById('speakToggle').classList.remove('on');
  }
  if (!autoAskEnabled) {
    autoAskEnabled = true;
    document.getElementById('askToggle').classList.add('on');
  }
  setConvState('idle');
  addMessage('[已自动开启] 在线对话 + 语音播报 + AI追问，可直接说话。', 'system');
  startListening();
  resetFollowUpChain();
  followUpTimer = setTimeout(async () => {
    followUpTimer = null;
    if (!convMode) return;
    if (convState === 'listening' && !voiceTranscript.trim() && autoAskEnabled) {
      await tryAskFollowUp();
    }
  }, 10000);
}

// ==================== 页面加载 ====================
if (authToken) {
  checkAuth().then(ok => {
    if (ok) {
      onLoginSuccess();
    } else {
      document.getElementById('loginOverlay').style.display = 'flex';
    }
  });
} else {
  document.getElementById('loginOverlay').style.display = 'flex';
}
