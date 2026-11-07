function readSession(key) {
  return sessionStorage.getItem(key);
}

function writeSession(key, value) {
  sessionStorage.setItem(key, value);
}

function removeSession(key) {
  sessionStorage.removeItem(key);
  localStorage.removeItem(key);
}

['access_token', 'refresh_token', 'current_user', 'demo_user', 'temp_token'].forEach((key) => {
  localStorage.removeItem(key);
});

window.API = window.API || (
  window.location.protocol === 'file:' ||
  ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)
    ? 'http://127.0.0.1:8000'
    : window.location.origin
);

window.NexaTenant = {
  REGISTRY_KEY: 'nexa_registered_users',

  // Comptes initiaux pré-configurés pour la démonstration
  getDefaultSeedUsers() {
    return [
      {
        id: 1,
        tenant_id: 'entreprise_demo',
        company_name: 'Nexa ERP Démo',
        username: 'Admin Principal',
        email: 'admin@nexa.local',
        password: 'admin',
        user_type: 'admin',
        is_active: true
      },
      {
        id: 2,
        tenant_id: 'entreprise_a',
        company_name: 'Société Alpha SARL',
        username: 'Direction Alpha',
        email: 'direction@alpha.com',
        password: 'password123',
        user_type: 'admin',
        is_active: true
      },
      {
        id: 3,
        tenant_id: 'entreprise_b',
        company_name: 'Groupe Beta SA',
        username: 'Direction Beta',
        email: 'contact@beta.com',
        password: 'password123',
        user_type: 'admin',
        is_active: true
      }
    ];
  },

  // Récupère la liste de tous les comptes enregistrés
  getRegisteredUsers() {
    try {
      const stored = localStorage.getItem(this.REGISTRY_KEY);
      if (stored) return JSON.parse(stored);
    } catch (e) {}
    const seeds = this.getDefaultSeedUsers();
    localStorage.setItem(this.REGISTRY_KEY, JSON.stringify(seeds));
    return seeds;
  },

  // Enregistre un nouvel utilisateur / entreprise dans le registre
  registerUser(userData) {
    const users = this.getRegisteredUsers();
    const existingIndex = users.findIndex(u => u.email.toLowerCase() === userData.email.toLowerCase());
    if (existingIndex >= 0) {
      users[existingIndex] = { ...users[existingIndex], ...userData };
    } else {
      users.push({
        id: userData.id || Date.now(),
        tenant_id: userData.tenant_id,
        company_name: userData.company_name || userData.tenant_id,
        username: userData.username || userData.email.split('@')[0],
        email: userData.email,
        password: userData.password,
        user_type: userData.user_type || 'admin',
        is_active: true,
        created_at: new Date().toISOString()
      });
    }
    localStorage.setItem(this.REGISTRY_KEY, JSON.stringify(users));
  },

  // Recherche un compte par email ou nom d'utilisateur
  findUser(emailOrUsername) {
    if (!emailOrUsername) return null;
    const term = emailOrUsername.trim().toLowerCase();
    const users = this.getRegisteredUsers();
    return users.find(u => 
      (u.email && u.email.toLowerCase() === term) ||
      (u.username && u.username.toLowerCase() === term)
    ) || null;
  },

  // Vérification stricte des identifiants (Mode Vérification)
  verifyCredentials(emailOrUsername, password) {
    const user = this.findUser(emailOrUsername);
    if (!user) {
      return {
        success: false,
        reason: 'not_found',
        message: "❌ Cet utilisateur n'est pas inscrit. Veuillez créer un espace entreprise d'abord."
      };
    }
    if (user.password && user.password !== password) {
      return {
        success: false,
        reason: 'bad_password',
        message: "❌ Mot de passe incorrect pour cet utilisateur."
      };
    }
    if (!user.is_active) {
      return {
        success: false,
        reason: 'inactive',
        message: "❌ Ce compte utilisateur a été désactivé par l'administrateur."
      };
    }
    return {
      success: true,
      user: user
    };
  },

  // Récupère l'utilisateur actuellement connecté
  getCurrentUser() {
    try {
      return JSON.parse(readSession('current_user') || '{}');
    } catch (e) {
      return {};
    }
  },

  // Détermine le Tenant ID actif
  getTenantId() {
    const token = readSession('access_token');
    if (token && token.includes('.')) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
        if (payload && payload.tenant_id) return payload.tenant_id;
      } catch (e) {}
    }
    const user = this.getCurrentUser();
    if (user && user.tenant_id) return user.tenant_id;

    if (user && user.email) {
      const parts = user.email.split('@');
      if (parts.length > 1) {
        return parts[1].split('.')[0].toLowerCase().replace(/[^a-z0-9]/g, '_');
      }
    }
    return 'entreprise_demo';
  },

  // Clé préfixée par entreprise : nexa_{tenant_id}_{resource}
  getStorageKey(resource) {
    const tenant = this.getTenantId();
    return `nexa_${tenant}_${resource}`;
  },

  // Lecture de données isolées par entreprise
  getData(resource, fallback = []) {
    const key = this.getStorageKey(resource);
    const stored = localStorage.getItem(key);
    if (stored !== null) {
      try { return JSON.parse(stored); } catch (e) { return fallback; }
    }
    // Si la ressource n'a jamais été initialisée pour ce tenant, on l'initialise
    this.setData(resource, fallback);
    return fallback;
  },

  // Écriture de données isolées par entreprise
  setData(resource, data) {
    const key = this.getStorageKey(resource);
    localStorage.setItem(key, JSON.stringify(data));
  },

  // Génération d'un token JWT valide pour le mode local
  createMockJWT(user) {
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
    const payload = btoa(JSON.stringify({
      sub: user.email,
      tenant_id: user.tenant_id,
      user_type: user.user_type || 'admin',
      username: user.username || user.company_name,
      exp: Math.floor(Date.now() / 1000) + 86400
    }));
    const sig = btoa(user.tenant_id + '_' + Date.now());
    return `${header}.${payload}.${sig}`;
  }
};

// Initialiser le registre si nécessaire dès le chargement
window.NexaTenant.getRegisteredUsers();

function getToken() {
  return readSession('access_token');
}

function getRefreshToken() {
  return readSession('refresh_token');
}

function saveTokens(access, refresh) {
  writeSession('access_token', access);
  if (refresh) writeSession('refresh_token', refresh);
}

function saveCurrentUser(user) {
  writeSession('current_user', JSON.stringify(user));
}

function clearTokens() {
  ['access_token', 'refresh_token', 'current_user', 'demo_user', 'temp_token'].forEach(removeSession);
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
  const token = getToken();
  if (token && !token.startsWith('demo_')) {
    try {
      await fetch(`${API}/auth/logout`, {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token }
      });
    } catch (e) {}
  }
  clearTokens();
  redirectToLogin();
}
const loginForm = document.getElementById('login-form');

if (loginForm) {
  const notice = sessionStorage.getItem('login_notice');
  const errorMsgBox = document.getElementById('error-msg');
  if (notice && errorMsgBox) {
    errorMsgBox.textContent = notice;
    errorMsgBox.style.display = 'block';
    sessionStorage.removeItem('login_notice');
  }
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Nettoie l'adresse e-mail avant de l'envoyer à l'API.
    const emailInput =
      document.getElementById('email')?.value?.trim().toLowerCase() || '';
    const password =
      document.getElementById('password')?.value || '';
    const errorMsg =
      document.getElementById('error-msg');

    if (!emailInput || !password) {
      if (errorMsg) {
        errorMsg.textContent =
          'Veuillez saisir votre email et votre mot de passe.';
        errorMsg.style.display = 'block';
      }
      return;
    }

    if (errorMsg) {
      errorMsg.style.display = 'none';
    }

    try {
      const formData = new FormData();
      formData.append('username', emailInput);
      formData.append('password', password);

      const response = await fetch(`${API}/auth/login`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        const detail =
          typeof data.detail === 'string'
            ? data.detail
            : 'E-mail ou mot de passe incorrect.';

        if (errorMsg) {
          errorMsg.textContent = detail;
          errorMsg.style.display = 'block';
        }
        return;
      }

      if (data.requires_2fa) {
        writeSession('temp_token', data.temp_token);
        window.location.href = '2fa.html';
        return;
      }

      saveTokens(data.access_token, data.refresh_token);

      let tenantId = 'default_tenant';
      let userType = 'admin';

      try {
        const payloadPart = data.access_token
          .split('.')[1]
          .replace(/-/g, '+')
          .replace(/_/g, '/');

        const payload = JSON.parse(atob(payloadPart));
        tenantId = payload.tenant_id || tenantId;
        userType = payload.user_type || userType;
      } catch (error) {
        console.error('Impossible de lire les informations du jeton.', error);
      }

      saveCurrentUser({
        username: emailInput.split('@')[0],
        email: emailInput,
        tenant_id: tenantId,
        user_type: userType,
        company_name: data.company_name || tenantId,
        database_name: data.database_name || null,
        logical_database_name: data.logical_database_name || null,
        environment_code: data.environment_code || null,
        workspace: data.workspace || 'entreprise'
      });

      window.location.href = 'dashboard.html';
    } catch (error) {
      console.error('Erreur de connexion au serveur :', error);

      if (errorMsg) {
        errorMsg.textContent =
          'Impossible de contacter le serveur. Vérifiez que FastAPI fonctionne sur http://127.0.0.1:8000.';
        errorMsg.style.display = 'block';
      }
    }
  });
}

const btnLogout = document.getElementById('btn-logout');
if (btnLogout) {
  btnLogout.addEventListener('click', logout);
}
