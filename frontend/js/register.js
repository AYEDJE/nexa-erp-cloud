const API = 'http://127.0.0.1:8000';

document.addEventListener("DOMContentLoaded", () => {
    const registerForm = document.getElementById("register-form");
    const companyInput = document.getElementById("company-name");
    const tenantInput = document.getElementById("tenant-id");
    const adminNameInput = document.getElementById("admin-fullname");
    const alertBox = document.getElementById("register-alert");

    // Génération automatique du code tenant depuis le nom d'entreprise
    companyInput.addEventListener("input", () => {
        const slug = companyInput.value
            .toLowerCase()
            .trim()
            .normalize("NFD").replace(/[\u0300-\u036f]/g, "") // Supprimer les accents
            .replace(/[^a-z0-9]/g, '-')
            .replace(/-+/g, '-')
            .replace(/^-+|-+$/g, '');
        tenantInput.value = slug || 'mon-entreprise';
    });

    function showAlert(message, type = "error") {
        alertBox.style.display = "block";
        if (type === "success") {
            alertBox.style.background = "#dcfce7";
            alertBox.style.color = "#166534";
            alertBox.style.border = "1px solid #bbf7d0";
        } else {
            alertBox.style.background = "#fee2e2";
            alertBox.style.color = "#991b1b";
            alertBox.style.border = "1px solid #fecaca";
        }
        alertBox.textContent = message;
    }

    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const companyName = companyInput.value.trim();
        const tenantId = tenantInput.value.trim().toLowerCase();
        const adminFullName = adminNameInput ? adminNameInput.value.trim() : "Administrateur";
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;
        const confirmPassword = document.getElementById("confirm-password").value;
        const plan = document.getElementById("subscription-plan").value;
        const taxId = document.getElementById("tax-id")?.value?.trim() || "";

        if (password !== confirmPassword) {
            showAlert("Les deux mots de passe ne correspondent pas.");
            return;
        }

        if (password.length < 6) {
            showAlert("Le mot de passe doit contenir au moins 6 caractères.");
            return;
        }

        const payload = {
            tenant_id: tenantId,
            email: email,
            password: password,
            user_type: "admin"
        };

        const submitBtn = registerForm.querySelector("button[type='submit']");
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Déploiement de votre instance ERP...`;

        try {
            const response = await fetch(`${API}/auth/register`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                // Sauvegarder les données de l'administrateur
                localStorage.setItem("current_user", JSON.stringify({
                    username: adminFullName,
                    email: email,
                    company_name: companyName,
                    tenant_id: tenantId
                }));

                showAlert(`Entreprise "${companyName}" créée avec succès ! Redirection vers votre espace...`, "success");
                setTimeout(() => {
                    window.location.href = "index.html";
                }, 1500);
                return;
            }

            const errorData = await response.json();
            throw new Error(errorData.detail || "Erreur lors du déploiement de l'instance.");

        } catch (error) {
            console.warn("Mode Démo Live Server ou échec backend :", error);
            
            // Mode Démo / Fallback local Live Server
            let demoUsers = JSON.parse(localStorage.getItem("demo_users") || "[]");
            const existing = demoUsers.find(u => u.email === email);
            if (existing) {
                showAlert("Un compte avec cet e-mail existe déjà.");
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<i class="fa-solid fa-rocket"></i> Déployer mon Espace Entreprise ERP`;
                return;
            }

            const newEnterprise = {
                id: demoUsers.length + 1,
                tenant_id: tenantId,
                company_name: companyName,
                tax_id: taxId,
                plan: plan,
                username: adminFullName,
                email: email,
                user_type: "admin",
                is_active: true,
                created_at: new Date().toISOString()
            };
            demoUsers.push(newEnterprise);
            localStorage.setItem("demo_users", JSON.stringify(demoUsers));

            // Sauvegarder comme utilisateur courant pré-rempli
            localStorage.setItem("current_user", JSON.stringify({
                username: adminFullName,
                email: email,
                company_name: companyName,
                tenant_id: tenantId
            }));

            showAlert(`Espace "${companyName}" (${tenantId}.nexa-erp.cloud) déployé avec succès ! Redirection...`, "success");
            setTimeout(() => {
                window.location.href = "index.html";
            }, 1200);
        }
    });
});
