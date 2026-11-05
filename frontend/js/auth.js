window.API = window.API || 'http://127.0.0.1:8000';
var API = window.API;

/**
 * ============================================================================
 * NEXA MULTI-TENANT ENGINE & REGISTRY
 * Isolation stricte des données par entreprise (Tenant) et vérification des comptes
 * ============================================================================
 */
window.NexaTenant = {
  REGISTRY_KEY: 'nexa_registered_users',

  // Comptes initiaux pré-configurés pour la démonstration
  getDefaultSeedUsers() {
    return [
      { id: 1, tenant_id: 'entreprise_demo', company_name: 'Nexa ERP Démo', username: 'Admin Principal', email: 'admin@nexa.local', password: 'admin', user_type: 'admin', is_active: true },
      { id: 2, tenant_id: 'entreprise_a', company_name: 'Société Alpha SARL', username: 'Direction Alpha', email: 'direction@alpha.com', password: 'password123', user_type: 'admin', is_active: true },
      { id: 3, tenant_id: 'entreprise_b', company_name: 'Groupe Beta SA', username: 'Direction Beta', email: 'contact@beta.com', password: 'password123', user_type: 'admin', is_active: true }
    ];
  },

  getRegisteredUsers() {
    try {
      const stored = localStorage.getItem(this.REGISTRY_KEY);
      if (stored) return JSON.parse(stored);
    } catch (e) {}
    const seeds = this.getDefaultSeedUsers();
    localStorage.setItem(this.REGISTRY_KEY, JSON.stringify(seeds));
    return seeds;
  },

  registerUser(userData) {
    const users = this.getRegisteredUsers();
    const existingIndex = users.findIndex(u => u.email.toLowerCase() === userData.email.toLowerCase());
    if (existingIndex >= 0) {
      users[existingIndex] = { ...users[existingIndex], ...userData };
    } else {
      users.push({
        id: userData.id || Date.now(), tenant_id: userData.tenant_id,
        company_name: userData.company_name || userData.tenant_id,
        username: userData.username || userData.email.split('@')[0],
        email: userData.email, password: userData.password,
        user_type: userData.user_type || 'admin', is_active: true,
        created_at: new Date().toISOString()
      });
    }
    localStorage.setItem(this.REGISTRY_KEY, JSON.stringify(users));
  },

  findUser(emailOrUsername) {
    if (!emailOrUsername) return null;
    const term = emailOrUsername.trim().toLowerCase();
    const users = this.getRegisteredUsers();
    return users.find(u =>
      (u.email && u.email.toLowerCase() === term) ||
      (u.username && u.username.toLowerCase() === term)
    ) || null;
  },

  verifyCredentials(emailOrUsername, password) {
    const user = this.findUser(emailOrUsername);
    if (!user) return { success: false, reason: 'not_found', message: "❌ Cet utilisateur n'est pas inscrit. Veuillez créer un espace entreprise d'abord." };
    if (user.password && user.password !== password) return { success: false, reason: 'bad_password', message: '❌ Mot de passe incorrect pour cet utilisateur.' };
    if (!user.is_active) return { success: false, reason: 'inactive', message: "❌ Ce compte utilisateur a été désactivé par l'administrateur." };
    return { success: true, user };
  },

  getCurrentUser() {
    try { return JSON.parse(localStorage.getItem('current_user') || '{}'); }
    catch (e) { return {}; }
  },

  getTenantId() {
    const user = this.getCurrentUser();
    if (user && user.tenant_id) return user.tenant_id;
    const token = localStorage.getItem('access_token');
    if (token && token.includes('.')) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
        if (payload && payload.tenant_id) return payload.tenant_id;
      } catch (e) {}
    }
    if (user && user.email) {
      const parts = user.email.split('@');
      if (parts.length > 1) return parts[1].split('.')[0].toLowerCase().replace(/[^a-z0-9]/g, '_');
    }
    return 'entreprise_demo';
  },

  getStorageKey(resource) { return `nexa_${this.getTenantId()}_${resource}`; },

  getData(resource, fallback = []) {
    const stored = localStorage.getItem(this.getStorageKey(resource));
    if (stored !== null) {
      try { return JSON.parse(stored); } catch (e) { return fallback; }
    }
    this.setData(resource, fallback);
    return fallback;
  },

  setData(resource, data) { localStorage.setItem(this.getStorageKey(resource), JSON.stringify(data)); },

  createMockJWT(user) {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payload = btoa(JSON.stringify({
      sub: user.email, tenant_id: user.tenant_id, user_type: user.user_type || 'admin',
      username: user.username || user.company_name, exp: Math.floor(Date.now() / 1000) + 86400
    }));
    const sig = btoa(user.tenant_id + '_' + Date.now());
    return `${header}.${payload}.${sig}`;
  }
};

window.NexaTenant.getRegisteredUsers();

function getToken() { return localStorage.getItem('access_token'); }
function getRefreshToken() { return localStorage.getItem('refresh_token'); }
function saveTokens(access, refresh) {
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
}
function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('current_user');
  localStorage.removeItem('demo_user');
}
function redirectToLogin() { window.location.href = 'index.html'; }
function guardPage() { if (!getToken()) redirectToLogin(); }

async function logout() {
  const token = getToken();
  if (token && !token.startsWith('demo_')) {
    try {
      await fetch(`${API}/auth/logout`, { method: 'POST', headers: { Authorization: 'Bearer ' + token } });
    } catch (e) {}
  }
  clearTokens();
  redirectToLogin();
}

const loginForm = document.getElementById('login-form');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    // L'inscription stocke les e-mails en minuscules. Normaliser aussi la saisie
    // du login évite une recherche différente selon les majuscules ou espaces.
    const emailInput = document.getElementById('email')?.value?.trim().toLowerCase() || '';
    const password = document.getElementById('password')?.value || '';
    const errorMsg = document.getElementById('error-msg');

    if (!emailInput || !password) {
      if (errorMsg) {
        errorMsg.textContent = 'Veuillez saisir votre email et votre mot de passe.';
        errorMsg.style.display = 'block';
      }
      return;
    }

    try {
      const formData = new FormData();
      formData.append('username', emailInput);
      formData.append('password', password);

      const res = await fetch(`${API}/auth/login`, { method: 'POST', body: formData });
      const data = await res.json();

      if (!res.ok) {
        const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        if (errorMsg) {
          errorMsg.textContent = detail || 'Identifiants incorrects ou compte non inscrit.';
          errorMsg.style.display = 'block';
        }
        return;
      }

      if (data.requires_2fa) {
        localStorage.setItem('temp_token', data.temp_token);
        window.location.href = '2fa.html';
        return;
      }

      saveTokens(data.access_token, data.refresh_token);
      let tenantId = 'default_tenant';
      let userType = 'admin';
      try {
        const payload = JSON.parse(atob(data.access_token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
        if (payload.tenant_id) tenantId = payload.tenant_id;
        if (payload.user_type) userType = payload.user_type;
      } catch (_) {}

      localStorage.setItem('current_user', JSON.stringify({
        username: emailInput.split('@')[0], email: emailInput,
        tenant_id: tenantId, user_type: userType
      }));
      window.location.href = 'dashboard.html';
    } catch (err) {
      // Backend inaccessible : mode local, uniquement pour une démonstration hors ligne.
      const verification = window.NexaTenant.verifyCredentials(emailInput, password);
      if (!verification.success) {
        if (errorMsg) {
          errorMsg.textContent = verification.message;
          errorMsg.style.display = 'block';
        }
        return;
      }
      const verifiedUser = verification.user;
      const token = window.NexaTenant.createMockJWT(verifiedUser);
      saveTokens(token, 'refresh_' + Date.now());
      localStorage.setItem('current_user', JSON.stringify({
        username: verifiedUser.username || verifiedUser.company_name,
        email: verifiedUser.email, tenant_id: verifiedUser.tenant_id,
        company_name: verifiedUser.company_name, user_type: verifiedUser.user_type || 'admin'
      }));
      window.location.href = 'dashboard.html';
    }
  });
}

const btnLogout = document.getElementById('btn-logout');
if (btnLogout) btnLogout.addEventListener('click', logout);
