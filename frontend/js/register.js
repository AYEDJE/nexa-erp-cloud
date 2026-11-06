
const API = 'http://127.0.0.1:8000';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('register-form');

  if (!form) {
    console.error("Formulaire register-form introuvable.");
    return;
  }

  const companyInput = document.getElementById('company-name');
  const tenantInput = document.getElementById('tenant-id');
  const alertBox = document.getElementById('register-alert');
  const submitBtn = form.querySelector("button[type='submit']");

  // Génération automatique du tenant ID
  if (companyInput && tenantInput) {
    companyInput.addEventListener('input', () => {
      const slug = companyInput.value
        .toLowerCase()
        .trim()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9]/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-+|-+$/g, '');

      tenantInput.value = slug || 'mon-entreprise';
    });
  }

  function showAlert(message, type = 'error') {
    if (!alertBox) {
      alert(message);
      return;
    }

    alertBox.style.display = 'block';
    alertBox.textContent = message;

    if (type === 'success') {
      alertBox.style.background = '#dcfce7';
      alertBox.style.color = '#166534';
      alertBox.style.border = '1px solid #bbf7d0';
    } else {
      alertBox.style.background = '#fee2e2';
      alertBox.style.color = '#991b1b';
      alertBox.style.border = '1px solid #fecaca';
    }
  }

  function setLoading(loading) {
    if (!submitBtn) return;

    submitBtn.disabled = loading;

    submitBtn.innerHTML = loading
      ? 'Création en cours...'
      : '<i class="fa-solid fa-rocket"></i> Déployer mon Espace Entreprise ERP';
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (alertBox) {
      alertBox.style.display = 'none';
    }

    const companyName =
      companyInput?.value.trim() || '';

    const tenantId =
      tenantInput?.value.trim().toLowerCase() || '';

    const legalStatus =
      document.getElementById('legal-status')?.value || 'SARL';

    const taxId =
      document.getElementById('tax-id')?.value.trim() || '';

    const adminFullName =
      document.getElementById('admin-fullname')?.value.trim() || 'Administrateur';

    const email =
      document.getElementById('email')?.value.trim().toLowerCase() || '';

    const password =
      document.getElementById('password')?.value || '';

    const confirmPassword =
      document.getElementById('confirm-password')?.value || '';

    const plan =
      document.getElementById('subscription-plan')?.value || 'business';

    // Vérifications
    if (!companyName || !tenantId || !email || !password) {
      showAlert('Veuillez remplir tous les champs obligatoires.');
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

    setLoading(true);

    try {
      // Enregistrement réel dans le backend
      const response = await fetch(`${API}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          tenant_id: tenantId,
          company_name: companyName,
          legal_form: legalStatus,
          tax_id: taxId || null,
          activity: document.getElementById('industry-sector')?.value || null,
          plan: plan,
          email: email,
          password: password,
          full_name: adminFullName,
          user_type: 'admin'
        })
      });

      const data = await response.json();

      // Toute erreur du backend arrête le processus
      if (!response.ok) {
        const detail =
          typeof data.detail === 'string'
            ? data.detail
            : JSON.stringify(data.detail);

        showAlert(
          detail || `Erreur d'inscription : HTTP ${response.status}`
        );

        return;
      }

      // Confirmation uniquement après réponse positive
      showAlert(
        `Espace entreprise « ${companyName} » créé avec succès !`,
        'success'
      );

      setTimeout(() => {
        window.location.href = 'index.html';
      }, 1500);

    } catch (error) {
      console.error('Erreur inscription :', error);

      showAlert(
        'Impossible de contacter le serveur. Vérifiez que FastAPI est démarré.'
      );

    } finally {
      setLoading(false);
    }
  });
});
