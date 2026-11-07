(function () {
  ['access_token', 'refresh_token', 'current_user', 'demo_user'].forEach((key) => localStorage.removeItem(key));

  const token        = sessionStorage.getItem('access_token');
  const refreshToken = sessionStorage.getItem('refresh_token');
  const API          = 'http://127.0.0.1:8000';

  if (!token) {
    window.location.href = 'index.html';
    return;
  }

  function decodeJWT(t) {
    try {
      const parts = t.split('.');
      if (parts.length >= 2) {
        const payload = parts[1].replace(/-/g, '+').replace(/_/g, '/');
        return JSON.parse(atob(payload));
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  function tokenEstExpire(t) {
    const payload = decodeJWT(t);
    if (!payload || !payload.exp) return false;
    return Date.now() >= payload.exp * 1000;
  }

  async function rafraichirToken() {
    if (!refreshToken) return false;
    try {
      const res = await fetch(`${API}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
      if (!res.ok) return false;
      const data = await res.json();
      sessionStorage.setItem('access_token', data.access_token);
      return true;
    } catch (e) {
      return false;
    }
  }

  function fermerSession(message) {
    sessionStorage.setItem('login_notice', message || 'Votre session est fermée. Reconnectez-vous.');
    ['access_token', 'refresh_token', 'current_user'].forEach((key) => {
      sessionStorage.removeItem(key);
      localStorage.removeItem(key);
    });
    window.location.href = 'index.html';
  }

  let idleMinutes = 30;
  let lastActivity = Date.now();
  ['click', 'keydown', 'mousemove'].forEach((eventName) => {
    document.addEventListener(eventName, () => { lastActivity = Date.now(); }, { passive: true });
  });

  async function verifier() {
    if (Date.now() - lastActivity > idleMinutes * 60 * 1000) {
      fermerSession(`Session fermée après ${idleMinutes} minutes d'inactivité. Reconnectez-vous.`);
      return;
    }
    if (tokenEstExpire(token)) {
      const ok = await rafraichirToken();
      if (!ok) {
        fermerSession('Session expirée. Reconnectez-vous.');
        return;
      }
    }
    try {
      const res = await fetch(`${API}/auth/session`, { headers: { Authorization: `Bearer ${sessionStorage.getItem('access_token') || token}` } });
      if (res.status === 401) {
        const data = await res.json().catch(() => ({}));
        fermerSession(typeof data.detail === 'string' ? data.detail : 'Cette session a été fermée.');
        return;
      }
      if (res.ok) {
        const data = await res.json();
        if (data.idle_minutes) idleMinutes = data.idle_minutes;
      }
    } catch (error) {}
  }

  verifier();
  setInterval(verifier, 60000);
})();
