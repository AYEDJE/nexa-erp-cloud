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
    // Données démo (uniquement si token démo)
    // ------------------------------------------------------------------
    function getDemoUsers() {
        const stored = localStorage.getItem("demo_tenant_users");
        if (stored) return JSON.parse(stored);
        const defaults = [
            { id: 1, full_name: "Administrateur", email: "admin@entreprise.com", role_name: "Administrateur Entreprise", user_type: "admin", is_active: true, is_two_factor_enabled: true },
            { id: 2, full_name: "Responsable Commercial", email: "commercial@entreprise.com", role_name: "Responsable Commercial", user_type: "staff", is_active: true, is_two_factor_enabled: false },
            { id: 3, full_name: "Comptable", email: "comptabilite@entreprise.com", role_name: "Responsable Financier & Comptable", user_type: "staff", is_active: true, is_two_factor_enabled: true },
            { id: 4, full_name: "Magasinier", email: "stock@entreprise.com", role_name: "Responsable des Stocks & Magasinier", user_type: "staff", is_active: true, is_two_factor_enabled: false },
            { id: 5, full_name: "Client Partenaire", email: "contact@client-partenaire.com", role_name: "Client Partenaire (Portail Externe)", user_type: "external", is_active: true, is_two_factor_enabled: false }
        ];
        localStorage.setItem("demo_tenant_users", JSON.stringify(defaults));
        return defaults;
    }

    // ------------------------------------------------------------------
    // Récupération des utilisateurs
    //   Retourne : un tableau (succès) ou null (erreur de chargement)
    // ------------------------------------------------------------------
    let currentUsers = [];

    async function fetchUsers() {
        if (isDemo) {
            const list = getDemoUsers();
            renderTable(list);
            updateKPIs(list);
            return list;
        }

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

            if (!res.ok) {
                const errData = await res.json().catch(() => null);
                throw new Error(formatApiError(errData, `Erreur ${res.status}`));
            }

            const data = await res.json();
            const users = Array.isArray(data) ? data : (data.items || data.users || data.data || []);
            renderTable(users);
            updateKPIs(users);
            return users;
        } catch (error) {
            console.error("Impossible de charger les utilisateurs :", error);
            currentUsers = [];
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:24px; color:#dc2626;">${escapeHtml(error.message)}</td></tr>`;
            updateKPIs([]);
            return null;          // null = erreur de chargement (différent d'une liste vide)
        }
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

        // ----- Mode démo -----
        if (isDemo) {
            const list = getDemoUsers();
            const newId = list.length > 0 ? Math.max(...list.map(u => u.id)) + 1 : 1;
            list.push({
                id: newId,
                full_name: fullName,
                email: email,
                role_name: ROLE_LABELS[roleVal],
                user_type: userType,
                is_active: true,
                is_two_factor_enabled: false
            });
            localStorage.setItem("demo_tenant_users", JSON.stringify(list));
            saveRole(email, roleVal);
            modal.style.display = "none";
            userForm.reset();
            fetchUsers();
            alert(tr("user_created", { email }));
            return;
        }

        // ----- Mode API réel : route protégée, le tenant vient du token -----
        const payload = {
            full_name: fullName,
            email: email,
            password: password,
            user_type: userType,
            role: roleVal
        };
        console.info("Création utilisateur — payload :", { ...payload, password: "***" });

        if (submitBtn) submitBtn.disabled = true;
        try {
            const res = await fetch(`${API}/users/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            if (res.status === 403) {
                throw new Error("Accès réservé aux administrateurs.");
            }
            if (!res.ok) {
                const errData = await res.json().catch(() => null);
                console.error("Réponse API (création utilisateur) :", res.status, errData);
                throw new Error(formatApiError(errData, `Erreur ${res.status} lors de l'inscription.`));
            }

            saveRole(email, roleVal);
            modal.style.display = "none";
            userForm.reset();

            const users = await fetchUsers();
            const visible = Array.isArray(users) && users.some(u => (u.email || "").toLowerCase() === email.toLowerCase());

            if (visible) {
                alert(tr("user_created", { email }));
            } else if (users === null) {
                alert(`Le compte "${email}" a été créé, mais la liste n'a pas pu être rechargée.\nLa raison est affichée dans le tableau de la page.`);
            } else {
                alert(`Le compte "${email}" a été créé mais n'apparaît pas dans la liste. Voir la console (F12).`);
            }
        } catch (error) {
            console.error(error);
            alert(tr("error_prefix", { msg: error.message }));
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    });

    // ------------------------------------------------------------------
    // Activer / désactiver un compte
    // ------------------------------------------------------------------
    async function handleToggleStatus(userId) {
        if (isDemo) {
            let list = getDemoUsers();
            list = list.map(u => String(u.id) === String(userId) ? { ...u, is_active: !u.is_active } : u);
            localStorage.setItem("demo_tenant_users", JSON.stringify(list));
            fetchUsers();
            return;
        }

        const u = currentUsers.find(x => String(x.id) === String(userId));
        if (!u) return;

        try {
            const res = await fetch(`${API}/users/${userId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ is_active: u.is_active === false })
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => null);
                throw new Error(formatApiError(errData, `Erreur ${res.status}`));
            }
            fetchUsers();
        } catch (err) {
            alert(tr("error_prefix", { msg: err.message }));
        }
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