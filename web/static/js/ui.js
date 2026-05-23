// ==================== 消息显示 ====================
function addMessage(text, role, showSpeak) {
  const area = document.getElementById('chatArea');
  const div = document.createElement('div');
  div.className = 'message ' + role;
  div.textContent = text;
  if (showSpeak && role === 'agent' && text.length > 20) {
    const btn = document.createElement('button');
    btn.className = 'msg-speak-btn';
    btn.innerHTML = '&#128266;';
    btn.title = '朗读';
    btn.onclick = (e) => { e.stopPropagation(); speakMessage(div, text); };
    div.appendChild(btn);
  }
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
  return div;
}

function showTyping() {
  const area = document.getElementById('chatArea');
  const div = document.createElement('div');
  div.className = 'typing-indicator';
  div.id = 'typing';
  div.innerHTML = '<span></span><span></span><span></span>';
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
  document.getElementById('sendBtn').disabled = true;
}

function removeTyping() {
  const el = document.getElementById('typing');
  if (el) el.remove();
  document.getElementById('sendBtn').disabled = false;
}

// ==================== 多模态弹窗 ====================
function toggleMediaModal() {
  const modal = document.getElementById('mediaModal');
  const btn = document.getElementById('mediaBtn');
  if (modal.classList.contains('show')) {
    closeMediaModal();
  } else {
    modal.classList.add('show');
    btn.classList.add('open');
  }
}

function openMediaModal(tab) {
  document.getElementById('mediaModal').classList.add('show');
  document.getElementById('mediaBtn').classList.add('open');
  switchMediaTab(tab);
}

function closeMediaModal() {
  document.getElementById('mediaModal').classList.remove('show');
  document.getElementById('mediaBtn').classList.remove('open');
  stopCamera();
}

function switchMediaTab(tab) {
  document.querySelectorAll('.modal .tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.modal .tab-content').forEach(c => c.classList.remove('active'));
  window.event.target.classList.add('active');
  document.getElementById('tab-' + tab).classList.add('active');
  if (tab !== 'camera') stopCamera();
}

document.addEventListener('click', function(e) {
  if (e.target.id === 'mediaModal') closeMediaModal();
});

// 拖拽支持
['dropDoc', 'dropAudio', 'dropVideo'].forEach(id => {
  const zone = document.getElementById(id);
  if (!zone) return;
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const type = id === 'dropDoc' ? 'document' : id === 'dropAudio' ? 'audio' : 'video';
      setSelectedFile(files[0], type);
    }
  });
});

function handleFileSelect(event, type) {
  const file = event.target.files[0];
  if (file) setSelectedFile(file, type);
}

function setSelectedFile(file, type) {
  selectedFile = file;
  selectedFileType = type;
  const statusId = type === 'document' ? 'docStatus' : type === 'audio' ? 'audioStatus' : 'videoStatus';
  const status = document.getElementById(statusId);
  if (status) {
    status.innerHTML = `<div style="padding:8px;background:rgba(56,189,248,.1);border-radius:6px;font-size:12px;color:#38bdf8;">
      [已选择] ${file.name} (${formatSize(file.size)})</div>`;
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes/1024).toFixed(1) + ' KB';
  return (bytes/1048576).toFixed(1) + ' MB';
}

async function uploadFile(type) {
  if (!selectedFile || selectedFileType !== type) {
    addMessage(`[上传] 请先选择${type === 'document' ? '文档' : type === 'audio' ? '音频' : '视频'}文件`, 'system');
    return;
  }
  closeMediaModal();
  addMessage(`[上传中] ${selectedFile.name}...`, 'system');
  showTyping();

  const formData = new FormData();
  formData.append('file', selectedFile);
  const endpoints = { document: '/api/upload/document', audio: '/api/upload/audio', video: '/api/upload/video' };

  try {
    const resp = await api(endpoints[type], { method: 'POST', body: formData });
    const data = await resp.json();
    removeTyping();
    if (data.status === 'ok') {
      addMessage(`[上传完成] ${data.message}`, 'system');
      if (data.preview) {
        addMessage(`[文档预览] ${data.preview.substring(0, 1000)}`, 'agent', true);
      }
      if (type === 'document' && data.preview) {
        showTyping();
        const chatResp = await api('/api/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            message: `请帮我分析这份文档的核心内容，提炼关键观点和行动建议。`,
            context_type: 'document',
            context_summary: `文档: ${data.filename}`
          })
        });
        const chatData = await chatResp.json();
        removeTyping();
        addMessage(chatData.analysis || '分析完成', 'agent', true);
      }
    }
    selectedFile = null;
    selectedFileType = null;
  } catch(e) {
    removeTyping();
    addMessage('上传失败: ' + e.message, 'system');
  }
}

// ==================== 摄像头 ====================
async function toggleCamera() {
  if (cameraStream) { stopCamera(); return; }
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    const video = document.getElementById('cameraPreview');
    video.srcObject = cameraStream;
    video.style.display = 'block';
    document.getElementById('cameraPlaceholder').style.display = 'none';
    document.getElementById('camToggleBtn').textContent = '关闭摄像头';
    document.getElementById('camCaptureBtn').disabled = false;
  } catch(e) {
    addMessage('[摄像头] 无法访问: ' + e.message + '。请检查权限设置。', 'system');
  }
}

function stopCamera() {
  if (cameraStream) { cameraStream.getTracks().forEach(t => t.stop()); cameraStream = null; }
  const preview = document.getElementById('cameraPreview');
  const placeholder = document.getElementById('cameraPlaceholder');
  if (preview) preview.style.display = 'none';
  if (placeholder) placeholder.style.display = 'block';
  document.getElementById('camToggleBtn').textContent = '开启摄像头';
  document.getElementById('camCaptureBtn').disabled = true;
}

async function captureCamera() {
  if (!cameraStream) return;
  const video = document.getElementById('cameraPreview');
  const canvas = document.getElementById('cameraCanvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  const imageData = canvas.toDataURL('image/png');
  try {
    const resp = await api('/api/upload/camera', {
      method: 'POST',
      body: JSON.stringify({ image: imageData })
    });
    const data = await resp.json();
    closeMediaModal();
    addMessage(`[摄像头] ${data.message}`, 'system');
  } catch(e) {
    addMessage('[摄像头] 上传失败: ' + e.message, 'system');
  }
}

// ==================== 画像 ====================
async function checkProfileStatus() {
  try {
    const resp = await api('/api/profile/status');
    const data = await resp.json();
    const summary = document.getElementById('profileSummary');

    if (data.complete) {
      summary.innerHTML = `
        <span style="color:#22c55e;">已完善 (${data.filled}/${data.total})</span><br>
        ${data.profile.role ? '角色: ' + data.profile.role + '<br>' : ''}
        ${data.profile.current_situation ? '处境: ' + data.profile.current_situation + '<br>' : ''}
        ${data.profile.emotional_state ? '情绪: ' + data.profile.emotional_state : ''}
      `;
      document.getElementById('roleInput').value = data.profile.role || '';
      document.getElementById('situationInput').value = data.profile.current_situation || '';
    } else {
      const pct = Math.round(data.filled / data.total * 100);
      summary.innerHTML = `<span style="color:#f59e0b;">完善度 ${pct}% (${data.filled}/${data.total})</span><br>点击下方按钮让AI通过对话了解你`;
      document.getElementById('roleInput').value = data.profile.role || '';
      document.getElementById('situationInput').value = data.profile.current_situation || '';
    }
  } catch(e) {}
}

async function askProfileQuestion() {
  showTyping();
  try {
    const resp = await api('/api/profile/discover');
    const data = await resp.json();
    removeTyping();
    if (data.question) {
      addMessage('[画像探索] ' + data.question, 'agent', true);
    }
  } catch(e) {
    removeTyping();
    addMessage('获取问题失败: ' + e.message, 'system');
  }
}

async function saveProfile() {
  const role = document.getElementById('roleInput').value.trim();
  const situation = document.getElementById('situationInput').value.trim();
  if (!role && !situation) return;
  try {
    await api('/api/profile', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({role, current_situation: situation, emotional_state: ''})
    });
    addMessage(`[OK] 个人画像已更新`, 'system');
    checkProfileStatus();
  } catch(e) { addMessage('更新失败: ' + e.message, 'system'); }
}

async function addGoal() {
  const input = document.getElementById('goalInput');
  const goal = input.value.trim();
  if (!goal) return;
  try {
    await api('/api/goals', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({goal, priority: 1})
    });
    input.value = '';
    addMessage(`[OK] 目标已添加: ${goal}`, 'system');
    loadGoals();
  } catch(e) { addMessage('添加失败: ' + e.message, 'system'); }
}

// ==================== 目标列表 ====================
async function loadGoals() {
  const container = document.getElementById('goalsList');
  if (!container) return;
  try {
    const resp = await api('/api/goals');
    const goals = await resp.json();
    if (!goals || goals.length === 0) {
      container.innerHTML = '<div style="font-size:11px;color:#64748b;">暂无活跃目标，开始你的第一个目标吧</div>';
      return;
    }
    container.innerHTML = goals.map(g => {
      const pct = g.progress || 0;
      let barClass = 'goal-bar-low';
      if (pct >= 75) barClass = 'goal-bar-high';
      else if (pct >= 30) barClass = 'goal-bar-mid';
      const daysAgo = g.created_at ? Math.floor((Date.now() - new Date(g.created_at).getTime()) / 86400000) : 0;
      const ageStr = daysAgo === 0 ? '今天' : daysAgo + '天前';
      return `<div class="goal-item" title="点击推进进度 | ${escHtml(g.goal)}">
        <div class="goal-meta"><span>${ageStr}</span><span>P${g.priority || 1}</span></div>
        <div class="goal-name-row" onclick="advanceGoal(${g.id},${pct})" style="cursor:pointer;">
          <span class="goal-name">${escHtml(g.goal)}</span>
          <span class="goal-pct">${pct}%</span>
          <button class="goal-assess" onclick="event.stopPropagation();assessGoal(${g.id})" title="专家评估">&#9733;</button>
          <button class="goal-del" onclick="event.stopPropagation();deleteGoal(${g.id})" title="删除">&times;</button>
        </div>
        <div class="goal-bar-outer"><div class="goal-bar-inner ${barClass}" style="width:${pct}%"></div></div>
      </div>`;
    }).join('');
  } catch(e) {
    container.innerHTML = '<div style="font-size:11px;color:#f87171;">加载失败</div>';
  }
}

async function deleteGoal(id) {
  try {
    await api('/api/goals/' + id, { method: 'DELETE' });
    loadGoals();
  } catch(e) { addMessage('删除失败: ' + e.message, 'system'); }
}

async function advanceGoal(id, currentPct) {
  const next = currentPct >= 100 ? 0 : Math.min(100, currentPct + 25);
  try {
    await api('/api/goals/' + id + '/progress', {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({progress: next})
    });
    loadGoals();
  } catch(e) { addMessage('更新进度失败: ' + e.message, 'system'); }
}

async function assessGoal(id) {
  addMessage('[评估] 正在对目标进行专家系统评估...', 'system');
  showTyping();
  try {
    const resp = await api('/api/goals/' + id + '/assess', { method: 'POST' });
    const data = await resp.json();
    removeTyping();

    const dims = data.dimension_scores || {};
    const dimLines = Object.entries(dims).map(([k, v]) => {
      const bar = '#'.repeat(Math.round(v.score / 10)) + '-'.repeat(10 - Math.round(v.score / 10));
      return `  ${k} [${bar}] ${v.score}分 (权重${(v.weight*100).toFixed(0)}%)`;
    }).join('\n');

    const weakLines = (data.weaknesses || []).length > 0
      ? '\n\n短板:\n' + data.weaknesses.map(w => `  ⚠ ${w.dimension}: ${w.score}分 (差${w.gap}分达标)`).join('\n')
      : '';

    const sugLines = (data.suggestions || []).length > 0
      ? '\n\n改进建议:\n' + data.suggestions.map(s => `  ▶ ${s.dimension}: ${s.action}`).join('\n')
      : '';

    const report = `[专家评估报告]\n综合达成率: ${data.composite_score}%\n\n维度得分:\n${dimLines}${weakLines}${sugLines}\n\n${data.feedback || ''}`;
    addMessage(report, 'agent', true);

    loadGoals();
    saveChatHistory();
  } catch(e) {
    removeTyping();
    addMessage('评估失败: ' + e.message, 'system');
  }
}

function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

async function addAbility() {
  const input = document.getElementById('abilityInput');
  const parts = input.value.trim().split(/\s+/);
  if (parts.length < 1) return;
  const name = parts[0];
  const level = parts[1] || 'beginner';
  try {
    await api('/api/abilities', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, level})
    });
    input.value = '';
    addMessage(`[OK] 能力已添加: ${name} (${level})`, 'system');
  } catch(e) { addMessage('添加失败: ' + e.message, 'system'); }
}
