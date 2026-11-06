const form = document.getElementById('twofa-form');
const codeInput = document.getElementById('twofa-code');
const errorBox = document.getElementById('twofa-error');

const tempToken = sessionStorage.getItem('temp_token') || localStorage.getItem('temp_token');
if (!tempToken) {
  window.location.href = 'index.html';
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.style.display = 'block';
}

if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.style.display = 'none';

    const code = codeInput.value.trim();
    if (!code) {
      showError('Veuillez saisir le code de validation 2FA.');
      return;
    }

    try {
      const res = await fetch(`${window.API}/auth/2fa/verify-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, temp_token: tempToken })
      });

      const data = await res.json();
      if (!res.ok) {
        showError(typeof data.detail === 'string' ? data.detail : 'Code 2FA invalide.');
        return;
      }

      sessionStorage.removeItem('temp_token');
      localStorage.removeItem('temp_token');
      sessionStorage.setItem('access_token', data.access_token);
      localStorage.setItem('access_token', data.access_token);
      sessionStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      const payload = JSON.parse(atob(data.access_token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      const profile = JSON.stringify({
        email: payload.sub,
        tenant_id: payload.tenant_id,
        user_type: payload.user_type || 'admin'
      });
      sessionStorage.setItem('current_user', profile);
      localStorage.setItem('current_user', profile);

      window.location.href = 'dashboard.html';
    } catch (err) {
      console.error('Erreur 2FA :', err);
      showError('Erreur de communication avec le serveur. Vérifiez le backend.');
    }
  });
}
