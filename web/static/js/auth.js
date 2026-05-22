// ==================== 认证 ====================
async function doLogin() {
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  const errEl = document.getElementById('loginError');
  try {
    const resp = await api('/api/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, password})
    });
    const data = await resp.json();
    if (resp.ok) {
      authToken = data.token;
      currentUser = data.username;
      localStorage.setItem('3hmind_token', authToken);
      onLoginSuccess();
    } else {
      errEl.textContent = data.error || '登录失败';
    }
  } catch(e) { errEl.textContent = '网络错误'; }
}

async function doRegister() {
  const username = document.getElementById('regUsername').value.trim();
  const password = document.getElementById('regPassword').value;
  const errEl = document.getElementById('regError');
  try {
    const resp = await api('/api/auth/register', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, password})
    });
    const data = await resp.json();
    if (resp.ok) {
      authToken = data.token;
      currentUser = data.username;
      localStorage.setItem('3hmind_token', authToken);
      onLoginSuccess();
    } else {
      errEl.textContent = data.error || '注册失败';
    }
  } catch(e) { errEl.textContent = '网络错误'; }
}

function showRegister() {
  document.getElementById('loginForm').style.display = 'none';
  document.getElementById('registerForm').style.display = 'block';
  document.getElementById('loginError').textContent = '';
  document.getElementById('regError').textContent = '';
}

function showLogin() {
  document.getElementById('loginForm').style.display = 'block';
  document.getElementById('registerForm').style.display = 'none';
  document.getElementById('loginError').textContent = '';
  document.getElementById('regError').textContent = '';
}

function logout() {
  authToken = '';
  currentUser = '';
  localStorage.removeItem('3hmind_token');
  if (convMode) toggleConversationMode();
  forceStopTTS();
  stopRecognition();
  if (inquiryActive) stopInquiry();
  document.getElementById('loginOverlay').style.display = 'flex';
  document.getElementById('loginForm').style.display = 'block';
  document.getElementById('registerForm').style.display = 'none';
  document.getElementById('loginUserInfo').style.display = 'none';
}

function onLoginSuccess() {
  document.getElementById('loginOverlay').style.display = 'none';
  document.getElementById('loginUserInfo').style.display = 'block';
  document.getElementById('loginUsername2').textContent = currentUser;
  if (!polling) {
    initApp();
  }
}

async function checkAuth() {
  if (!authToken) return false;
  try {
    const resp = await api('/api/auth/me');
    if (resp.ok) {
      const data = await resp.json();
      currentUser = data.username;
      return true;
    }
  } catch(e) {}
  authToken = '';
  localStorage.removeItem('3hmind_token');
  return false;
}
