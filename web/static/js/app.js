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
  // 恢复对话历史（sessionStorage 在关闭标签页后自动清除）
  restoreChatHistory();

  // 刷新页面时强制重置 AI 追问
  resetFollowUpChain();
  if (followUpTimer) { clearTimeout(followUpTimer); followUpTimer = null; }
  _followUpCount = 0;

  setupResizer();
  startPolling();
  checkProfileStatus();
  loadGoals();

  // 不自动开启在线对话模式，让用户手动开启
  try {
    const resp = await api('/api/profile/status');
    const data = await resp.json();
    if (!data.complete) {
      const discResp = await api('/api/profile/discover');
      const discData = await discResp.json();
      if (discData.question) {
        addMessage('[画像探索] ' + discData.question, 'agent', true);
        saveChatHistory();
      }
    }
  } catch(e) {}
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

// ==================== 侧边栏宽度可调节 ====================
function setupResizer() {
  const sidebar = document.querySelector('.sidebar');
  const handle = document.getElementById('resizeHandle');
  if (!sidebar || !handle) return;

  // 从 localStorage 恢复宽度
  const saved = localStorage.getItem('3hmind_sidebar_width');
  if (saved) sidebar.style.width = saved + 'px';

  let dragging = false;
  let startX = 0;
  let startW = 0;

  handle.addEventListener('mousedown', (e) => {
    dragging = true;
    startX = e.clientX;
    startW = sidebar.offsetWidth;
    handle.classList.add('active');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const newW = Math.max(180, Math.min(500, startW + e.clientX - startX));
    sidebar.style.width = newW + 'px';
  });

  document.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    handle.classList.remove('active');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    localStorage.setItem('3hmind_sidebar_width', sidebar.offsetWidth);
  });
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
