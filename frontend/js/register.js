const API = 'http://127.0.0.1:8000';

document.addEventListener('DOMContentLoaded', () => {
  const form          = document.getElementById('register-form');
  const companyInput  = document.getElementById('company-name');
  const tenantInput   = document.getElementById('tenant-id');
  const alertBox      = document.getElementById('register-alert');
  const submitBtn     = form.querySelector("button[type='submit']");

  // Génération automatique du code tenant depuis le nom d'entreprise
  if (companyInput && tenantInput) {
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
  }

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

    const companyName     = companyInput ? companyInput.value.trim() : '';
    const legalStatus     = document.getElementById('legal-status')?.value || 'SARL';
    const tenantId        = tenantInput ? tenantInput.value.trim().toLowerCase() : '';
    const taxId           = document.getElementById('tax-id')?.value?.trim() || '';
    const adminFullName   = document.getElementById('admin-fullname')?.value?.trim() || 'Administrateur';
    const email           = document.getElementById('email')?.value?.trim().toLowerCase() || '';
    const password        = document.getElementById('password')?.value || '';
    const confirmPassword = document.getElementById('confirm-password')?.value || '';
    const plan            = document.getElementById('subscription-plan')?.value || 'business';

    if (!tenantId) {
      showAlert("L'identifiant cloud est obligatoire.");
      return;
    }

    if (password !== confirmPassword) {
      showAlert('Les deux mots de passe ne correspondent pas.');
      return;
    }

    if (password.length < 6) {
      showAlert('Le mot de passe doit contenir au moins 6 caractères.');
      return;
    }

    // Vérifier si l'email existe déjà dans le registre local
    if (window.NexaTenant) {
      const existing = window.NexaTenant.findUser(email);
      if (existing) {
        showAlert("Un compte avec cet e-mail existe déjà. Veuillez vous connecter ou utiliser un autre e-mail.");
        return;
      }
    }

    setBoutonChargement(true);

    const newUserData = {
      tenant_id: tenantId,
      company_name: companyName,
      username: adminFullName,
      email: email,
      password: password,
      user_type: 'admin',
      tax_id: taxId,
      plan: plan,
      is_active: true
    };

    // 1. Tenter l'enregistrement sur le backend (s'il tourne)
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

      if (!res.ok) {
        const data = await res.json();
        // Si le backend répond avec une erreur (ex: email déjà pris sur la DB), on affiche l'erreur
        if (res.status === 400 && data.detail && data.detail.includes("déjà")) {
          showAlert(data.detail);
          setBoutonChargement(false);
          return;
        }
      }
    } catch (err) {
      // Backend non accessible -> on continue en mode local
      console.info("Backend non joignable, enregistrement dans l'instance locale multi-tenant.");
    }

    // 2. Enregistrer l'entreprise et l'administrateur dans le registre multi-tenant
    if (window.NexaTenant) {
      window.NexaTenant.registerUser(newUserData);

      // Initialiser un espace vierge et 100% isolé pour cette nouvelle entreprise
      const prevTenant = window.NexaTenant.getCurrentUser()?.tenant_id;
      
      // Initialisation explicite des clés de cette entreprise
      localStorage.setItem(`nexa_${tenantId}_clients`, JSON.stringify([]));
      localStorage.setItem(`nexa_${tenantId}_products`, JSON.stringify([]));
      localStorage.setItem(`nexa_${tenantId}_invoices`, JSON.stringify([]));
      localStorage.setItem(`nexa_${tenantId}_users`, JSON.stringify([
        {
          id: 1,
          email: email,
          role_name: "Administrateur Entreprise",
          user_type: "admin",
          is_active: true,
          is_two_factor_enabled: false
        }
      ]));
      localStorage.setItem(`nexa_${tenantId}_company`, JSON.stringify({
        name: companyName,
        legal_form: legalStatus,
        tax_id: taxId,
        email: email,
        tenant_id: tenantId
      }));
    }

    showAlert(`✅ Espace entreprise « ${companyName} » (${tenantId}) créé avec succès ! Redirection vers la page de connexion...`, 'success');
    setTimeout(() => {
      window.location.href = 'index.html';
    }, 1500);
  });
});
