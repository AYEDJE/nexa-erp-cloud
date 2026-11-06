(function () {
  if (!sessionStorage.getItem('access_token') && localStorage.getItem('access_token')) {
    sessionStorage.setItem('access_token', localStorage.getItem('access_token'));
    ['refresh_token', 'current_user', 'demo_user'].forEach((key) => {
      const value = localStorage.getItem(key);
      if (value) sessionStorage.setItem(key, value);
    });
  }

  const token        = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
  const refreshToken = sessionStorage.getItem('refresh_token') || localStorage.getItem('refresh_token');
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
      localStorage.setItem('access_token', data.access_token);
      return true;
    } catch (e) {
      return false;
    }
  }

  async function verifier() {
    if (tokenEstExpire(token)) {
      const ok = await rafraichirToken();
      if (!ok) {
        // Déconnexion propre : on ne supprime QUE la session, pas la base des entreprises
        ['access_token', 'refresh_token', 'current_user'].forEach((key) => {
          sessionStorage.removeItem(key);
          localStorage.removeItem(key);
        });
        window.location.href = 'index.html';
      }
    }
  }

  verifier();
})();
