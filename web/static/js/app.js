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

function setupIdleFollowUp() {
  const input = document.getElementById('chatInput');
  if (!input) return;

  // 用户开始输入时重置追问计时器
  function resetOnActivity() {
    if (!autoAskEnabled) return;
    if (followUpTimer) {
      clearTimeout(followUpTimer);
      followUpTimer = null;
    }
    // 如果输入框有内容，不重新调度 — 等用户发送后再由 sendChat/sendStreamChat 调度
    const hasText = input.value.trim().length > 0;
    if (!hasText && _followUpCount < MAX_FOLLOW_UPS) {
      // 空输入框说明用户已发送消息，由 chat 完成处理调度
      // 不做任何事
    }
  }

  input.addEventListener('input', resetOnActivity);
  input.addEventListener('focus', resetOnActivity);
  input.addEventListener('keydown', (e) => {
    // 非回车键说明用户在输入，重置追问
    if (e.key !== 'Enter') resetOnActivity();
  });
}

async function initApp() {
  // 恢复对话历史（sessionStorage 在关闭标签页后自动清除）
  restoreChatHistory();

  // 刷新页面时强制重置 AI 追问
  resetFollowUpChain();
  if (followUpTimer) { clearTimeout(followUpTimer); followUpTimer = null; }
  _followUpCount = 0;

  setupResizer();
  setupIdleFollowUp();
  startPolling();
  checkProfileStatus();
  loadGoals();

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
