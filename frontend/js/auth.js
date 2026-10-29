const API = 'http://127.0.0.1:8000';

const DEMO_MODE = true;

function getToken() {
  return localStorage.getItem('access_token');
}

function getRefreshToken() {
  return localStorage.getItem('refresh_token');
}

function saveTokens(access, refresh) {
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
}

function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('demo_user');
  localStorage.removeItem('current_user');
}

function redirectToLogin() {
  window.location.href = 'index.html';
}

function guardPage() {
  if (!getToken()) {
    redirectToLogin();
  }
}

async function logout() {
  if (!DEMO_MODE) {
    try {
      await fetch(`${API}/auth/logout`, {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + getToken() }
      });
    } catch (e) {}
  }
  clearTokens();
  redirectToLogin();
}

const loginForm = document.getElementById('login-form');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const usernameInput = document.getElementById('username')?.value?.trim() || '';
    const emailInput    = document.getElementById('email')?.value?.trim() || '';
    const password      = document.getElementById('password')?.value || '';
    const errorMsg      = document.getElementById('error-msg');

    const displayName = usernameInput || (emailInput ? emailInput.split('@')[0] : 'Admin');
    const finalEmail = emailInput || `${displayName.toLowerCase().replace(/\s+/g, '.')}@nexa.local`;

    // ========== MODE DÉMO ==========
    if (DEMO_MODE) {
      const fakeToken = 'demo_' + btoa(finalEmail) + '_' + Date.now();

      saveTokens(fakeToken, 'demo_refresh_' + Date.now());
      const userData = {
        username: displayName,
        email: finalEmail,
        is_demo: true
      };
      localStorage.setItem('demo_user', JSON.stringify(userData));
      localStorage.setItem('current_user', JSON.stringify(userData));

      window.location.href = 'dashboard.html';
      return;
    }

    // ========== MODE NORMAL ==========
    const formData = new FormData();
    formData.append('username', finalEmail);
    formData.append('password', password);

    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        body: formData
      });

      const data = await res.json();

      if (!res.ok) {
        const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        errorMsg.textContent = (detail || 'Erreur de connexion.') +
          ' [debug : code ' + res.status + ', email = "' + finalEmail + '"]';
        errorMsg.style.display = 'block';
        return;
      }

      if (data.requires_2fa) {
        localStorage.setItem('temp_token', data.temp_token);
        window.location.href = '2fa.html';
        return;
      }

      saveTokens(data.access_token, data.refresh_token);
      localStorage.setItem('current_user', JSON.stringify({
        username: displayName,
        email: finalEmail
      }));
      window.location.href = 'dashboard.html';

    } catch (err) {
      errorMsg.textContent = 'Impossible de joindre le serveur backend.';
      errorMsg.style.display = 'block';
    }
  });
}

const btnLogout = document.getElementById('btn-logout');
if (btnLogout) {
  btnLogout.addEventListener('click', logout);
}
