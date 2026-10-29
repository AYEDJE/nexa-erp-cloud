const API = 'http://127.0.0.1:8000';

document.addEventListener('DOMContentLoaded', () => {
  const form          = document.getElementById('register-form');
  const companyInput  = document.getElementById('company-name');
  const tenantInput   = document.getElementById('tenant-id');
  const alertBox      = document.getElementById('register-alert');
  const submitBtn     = form.querySelector("button[type='submit']");

  companyInput.addEventListener('input', () => {
    const slug = companyInput.value
      .toLowerCase()
      .trim()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-+|-+$/g, '');
    tenantInput.value = slug || 'mon-entreprise';
  });

  function showAlert(message, type = 'error') {
    alertBox.style.display = 'block';
    if (type === 'success') {
      alertBox.style.background = '#dcfce7';
      alertBox.style.color      = '#166534';
      alertBox.style.border     = '1px solid #bbf7d0';
    } else {
      alertBox.style.background = '#fee2e2';
      alertBox.style.color      = '#991b1b';
      alertBox.style.border     = '1px solid #fecaca';
    }
    alertBox.textContent = message;
  }

  function setBoutonChargement(loading) {
    submitBtn.disabled = loading;
    submitBtn.innerHTML = loading
      ? '<i class="fa-solid fa-spinner fa-spin"></i> Déploiement en cours...'
      : '<i class="fa-solid fa-rocket"></i> Déployer mon Espace Entreprise ERP';
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    alertBox.style.display = 'none';

    const email           = document.getElementById('email').value.trim();
    const password        = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    const tenantId        = tenantInput.value.trim().toLowerCase();

    if (!tenantId) {
      showAlert("L'identifiant cloud est obligatoire.");
      return;
    }

    if (password !== confirmPassword) {
      showAlert('Les deux mots de passe ne correspondent pas.');
      return;
    }

    if (password.length < 8) {
      showAlert('Le mot de passe doit contenir au moins 8 caractères.');
      return;
    }

    setBoutonChargement(true);

    try {
      const res = await fetch(`${API}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id:  tenantId,
          email:      email,
          password:   password,
          user_type:  'admin'
        })
      });

      const data = await res.json();

      if (!res.ok) {
        showAlert(data.detail || "Erreur lors de la création du compte.");
        setBoutonChargement(false);
        return;
      }

      showAlert('Espace entreprise créé avec succès ! Redirection vers la connexion...', 'success');
      setTimeout(() => {
        window.location.href = 'index.html';
      }, 1500);

    } catch (err) {
      showAlert('Impossible de joindre le serveur. Vérifiez que le backend est démarré.');
      setBoutonChargement(false);
    }
  });
});