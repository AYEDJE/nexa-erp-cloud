const API = window.API || 'http://127.0.0.1:8000';

document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    const tr = (k, p) => (window.i18n ? window.i18n.t(k, p) : k);

    const tableBody = document.getElementById("users-table-body");
    const modal = document.getElementById("user-modal");
    const openModalBtn = document.getElementById("open-user-modal");
    const closeModalBtn = document.getElementById("close-modal");
    const userForm = document.getElementById("user-form");

    const kpiTotal = document.getElementById("kpi-total-users");
    const kpiStaff = document.getElementById("kpi-staff-count");
    const kpiExternal = document.getElementById("kpi-external-count");
    const kpiMfa = document.getElementById("kpi-mfa-count");

    const isDemo = token.startsWith("demo_");
    const ROLES_KEY = "user_roles";   // mémorise le rôle choisi : { "email": "commercial" }

    // ------------------------------------------------------------------
    // Utilitaires
    // ------------------------------------------------------------------
    function formatApiError(data, fallback) {
        if (!data) return fallback;
        const d = data.detail !== undefined ? data.detail
                : data.message !== undefined ? data.message
                : data;
        if (typeof d === "string") return d;
        if (Array.isArray(d)) {
            return d.map(e => {
                if (typeof e === "string") return e;
                const field = Array.isArray(e.loc) ? e.loc.filter(x => x !== "body" && x !== "query").join(" → ") : "";
                return (field ? field + " : " : "") + (e.msg || JSON.stringify(e));
            }).join("\n");
        }
        try { return JSON.stringify(d); } catch (_) { return fallback; }
    }

    function escapeHtml(s) {
        return String(s ?? "").replace(/[&<>"']/g, c => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        }[c]));
    }

    function getSavedRoles() {
        try { return JSON.parse(localStorage.getItem(ROLES_KEY)) || {}; } catch (_) { return {}; }
    }
    function saveRole(email, roleVal) {
        const roles = getSavedRoles();
        roles[email.toLowerCase()] = roleVal;
        localStorage.setItem(ROLES_KEY, JSON.stringify(roles));
    }

    const ROLE_LABELS = {
        commercial: "Responsable Commercial",
        finance: "Responsable Financier et Comptable",
        stock: "Responsable des Stocks et Magasinier",
        achats: "Responsable des Achats",
        staff: "Collaborateur Standard",
        admin: "Administrateur Adjoint",
        client_ext: "Client Partenaire",
        supplier_ext: "Fournisseur Agréé"
    };

    // ------------------------------------------------------------------
    // ------------------------------------------------------------------
    // Données isolées par entreprise (Multi-Tenant)
    // ------------------------------------------------------------------
    function getTenantUsers() {
        const tenantId = window.NexaTenant ? window.NexaTenant.getTenantId() : 'default';
        const isSeedDemo = (tenantId === 'entreprise_demo');
        const currentUser = window.NexaTenant ? window.NexaTenant.getCurrentUser() : {};
        const fallback = isSeedDemo ? [
            { id: 1, full_name: "Administrateur Démo", email: "admin@nexa.local", role_name: "Administrateur Entreprise", user_type: "admin", is_active: true, is_two_factor_enabled: true },
            { id: 2, full_name: "Responsable Commercial", email: "commercial@nexa.local", role_name: "Responsable Commercial", user_type: "staff", is_active: true, is_two_factor_enabled: false }
        ] : [
            { id: 1, full_name: (currentUser.username || currentUser.company_name || "Administrateur"), email: (currentUser.email || "admin@entreprise.com"), role_name: "Administrateur Entreprise", user_type: "admin", is_active: true, is_two_factor_enabled: false }
        ];

        if (window.NexaTenant) {
            return window.NexaTenant.getData('users', fallback);
        }
        const key = `nexa_${tenantId}_users`;
        const stored = localStorage.getItem(key);
        return stored ? JSON.parse(stored) : fallback;
    }

    function saveTenantUsers(list) {
        if (window.NexaTenant) {
            window.NexaTenant.setData('users', list);
        } else {
            const tenantId = 'default';
            localStorage.setItem(`nexa_${tenantId}_users`, JSON.stringify(list));
        }
    }

    // ------------------------------------------------------------------
    // Récupération des utilisateurs
    //   Retourne : un tableau (succès) ou null (erreur de chargement)
    // ------------------------------------------------------------------
    let currentUsers = [];

    async function fetchUsers() {
        try {
            const res = await fetch(`${API}/users/`, {
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (res.status === 401) {
                localStorage.removeItem("access_token");
                window.location.href = "index.html";
                return null;
            }

            if (res.status === 403) {
                throw new Error("Accès réservé aux administrateurs. Votre compte n'a pas les droits pour gérer les utilisateurs.");
            }

            if (res.ok) {
                const data = await res.json();
                const users = Array.isArray(data) ? data : (data.items || data.users || data.data || []);
                saveTenantUsers(users);
                renderTable(users);
                updateKPIs(users);
                return users;
            }
        } catch (error) {
            // Backend non disponible ou erreur réseau -> repli sur la base isolée du tenant
        }

        const list = getTenantUsers();
        renderTable(list);
        updateKPIs(list);
        return list;
    }

    function updateKPIs(list) {
        if (!list) return;
        const total = list.length;
        const staff = list.filter(u => u.user_type === "staff" || u.user_type === "admin").length;
        const external = list.filter(u => u.user_type === "external").length;
        const mfa = list.filter(u => u.is_two_factor_enabled).length;

        if (kpiTotal) kpiTotal.textContent = total;
        if (kpiStaff) kpiStaff.textContent = staff;
        if (kpiExternal) kpiExternal.textContent = external;
        if (kpiMfa) kpiMfa.textContent = mfa;
    }

    // ------------------------------------------------------------------
    // Affichage
    // ------------------------------------------------------------------
    function getRoleBadge(user) {
        const saved = getSavedRoles()[(user.email || "").toLowerCase()];
        const role = (user.role_name || user.role || saved || user.user_type || "").toLowerCase();

        if (saved === "achats" || role.includes("achat"))
            return `<span class="role-badge role-staff"><i class="fa-solid fa-cart-shopping"></i> Achats</span>`;
        if (user.user_type === "external" || saved === "client_ext" || saved === "supplier_ext" || role.includes("client") || role.includes("fournisseur"))
            return `<span class="role-badge role-external"><i class="fa-solid fa-globe"></i> Portail Tiers</span>`;
        if (role.includes("admin"))
            return `<span class="role-badge role-admin"><i class="fa-solid fa-shield-halved"></i> Admin</span>`;
        if (role.includes("commercial"))
            return `<span class="role-badge role-commercial"><i class="fa-solid fa-briefcase"></i> Commercial</span>`;
        if (role.includes("finance") || role.includes("financier") || role.includes("compta"))
            return `<span class="role-badge role-finance"><i class="fa-solid fa-coins"></i> Finance</span>`;
        if (role.includes("stock") || role.includes("magasin"))
            return `<span class="role-badge role-stock"><i class="fa-solid fa-boxes-stacked"></i> Magasinier</span>`;
        return `<span class="role-badge role-staff"><i class="fa-solid fa-user"></i> Collaborateur</span>`;
    }

    function renderTable(users) {
        currentUsers = users || [];
        if (!users || users.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 24px; color: #6b7280;">Aucun utilisateur trouvé. Cliquez sur "Inscrire un Utilisateur" pour débuter.</td></tr>`;
            return;
        }

        tableBody.innerHTML = users.map(u => {
            const statusClass = u.is_active === false ? "status-inactive" : "status-active";
            const statusLabel = u.is_active === false ? "Désactivé" : "Actif";
            const perimeter = u.user_type === "external" ? "Portail Externe" : "Interne Entreprise";
            const savedKey = getSavedRoles()[(u.email || "").toLowerCase()];
            const roleText = u.role_name || u.role || (savedKey ? ROLE_LABELS[savedKey] : "") || u.user_type || "";
            const shownName = u.full_name || (u.email ? u.email.split("@")[0] : "—");
            const initials = shownName.split(/\s+/).slice(0, 2).map(w => w[0] || "").join("").toUpperCase();
            const mfaIcon = u.is_two_factor_enabled
                ? `<span style="color:#16a34a; font-weight:600; font-size:12px;"><i class="fa-solid fa-lock"></i> Activé</span>`
                : `<span style="color:#94a3b8; font-size:12px;"><i class="fa-solid fa-unlock"></i> Non configuré</span>`;

            return `
            <tr>
                <td><strong>#${escapeHtml(u.id)}</strong></td>
                <td>
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="width:34px; height:34px; border-radius:50%; background:#dbeafe; color:#1e40af; display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:12px; flex-shrink:0;">${escapeHtml(initials)}</span>
                        <div>
                            <div style="font-weight:600; color:#111827;">${escapeHtml(shownName)}</div>
                            <small style="color:#64748b;">${escapeHtml(u.email)} · ${escapeHtml(roleText)}</small>
                        </div>
                    </div>
                </td>
                <td>${getRoleBadge(u)}</td>
                <td><small style="font-weight:500; color:#475569;">${perimeter}</small></td>
                <td>${mfaIcon}</td>
                <td><span class="status-pill ${statusClass}">${statusLabel}</span></td>
                <td style="text-align: center;">
                    <button class="toggle-status-btn" data-id="${escapeHtml(u.id)}" style="background:none; border:1px solid #cbd5e1; border-radius:6px; padding:4px 8px; cursor:pointer; font-size:12px; color:#475569;" title="Changer l'état du compte">
                        ${u.is_active === false ? "Réactiver" : "Désactiver"}
                    </button>
                </td>
            </tr>
            `;
        }).join("");

        document.querySelectorAll(".toggle-status-btn").forEach(btn => {
            btn.addEventListener("click", () => handleToggleStatus(btn.dataset.id));
        });
    }

    // ------------------------------------------------------------------
    // Inscription d'un nouveau collaborateur
    // ------------------------------------------------------------------
    userForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const submitBtn = userForm.querySelector("button[type='submit']");
        const fullName = (document.getElementById("new-fullname")?.value || "").trim();
        const email = document.getElementById("new-email").value.trim();
        const roleVal = document.getElementById("new-role").value;
        const password = document.getElementById("new-password").value;
        const confirmPassword = document.getElementById("confirm-user-password").value;

        if (password !== confirmPassword) {
            alert(tr("pw_mismatch"));
            return;
        }
        if (password.length < 8) {
            alert(tr("Le mot de passe doit contenir au moins 8 caractères."));
            return;
        }

        let userType = "staff";
        if (roleVal === "admin") userType = "admin";
        else if (roleVal === "client_ext" || roleVal === "supplier_ext") userType = "external";

        // Sauvegarde locale isolée pour l'entreprise connectée
        const list = getTenantUsers();
        const newId = list.length > 0 ? Math.max(...list.map(u => u.id)) + 1 : 1;
        const newUser = {
            id: newId,
            full_name: fullName,
            email: email,
            role_name: ROLE_LABELS[roleVal] || roleVal,
            user_type: userType,
            is_active: true,
            is_two_factor_enabled: false
        };
        list.push(newUser);
        saveTenantUsers(list);
        saveRole(email, roleVal);

        // Enregistrer dans le registre global pour permettre la connexion du collaborateur
        if (window.NexaTenant) {
            const tenantId = window.NexaTenant.getTenantId();
            window.NexaTenant.registerUser({
                email: email,
                password: password,
                username: fullName,
                tenant_id: tenantId,
                company_name: window.NexaTenant.getCurrentUser()?.company_name || tenantId,
                role_name: ROLE_LABELS[roleVal] || roleVal,
                user_type: userType,
                is_active: true
            });
        }

        // Tentative de synchronisation vers le backend
        const payload = {
            full_name: fullName,
            email: email,
            password: password,
            user_type: userType,
            role: roleVal
        };

        if (submitBtn) submitBtn.disabled = true;
        try {
            await fetch(`${API}/users/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });
        } catch (_) {}

        modal.style.display = "none";
        userForm.reset();
        fetchUsers();
        alert(tr("user_created", { email }));
        if (submitBtn) submitBtn.disabled = false;
    });

    // ------------------------------------------------------------------
    // Activer / désactiver un compte
    // ------------------------------------------------------------------
    async function handleToggleStatus(userId) {
        let list = getTenantUsers();
        const target = list.find(u => String(u.id) === String(userId));
        if (target) {
            target.is_active = !target.is_active;
            saveTenantUsers(list);

            if (window.NexaTenant) {
                window.NexaTenant.registerUser({
                    email: target.email,
                    is_active: target.is_active
                });
            }
        }

        try {
            if (target) {
                await fetch(`${API}/users/${userId}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                    body: JSON.stringify({ is_active: target.is_active })
                });
            }
        } catch (_) {}

        fetchUsers();
    }

    // ------------------------------------------------------------------
    // Modale
    // ------------------------------------------------------------------
    if (openModalBtn) {
        openModalBtn.addEventListener("click", () => {
            userForm.reset();
            modal.style.display = "block";
        });
    }
    if (closeModalBtn) {
        closeModalBtn.addEventListener("click", () => { modal.style.display = "none"; });
    }
    window.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
    });

    // Re-dessiner le tableau quand la langue change
    document.addEventListener("langchange", () => {
        if (currentUsers.length) renderTable(currentUsers);
    });

    fetchUsers();
});