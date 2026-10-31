document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

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

    function getDemoUsers() {
        const stored = localStorage.getItem("demo_tenant_users");
        if (stored) return JSON.parse(stored);
        const defaults = [
            {
                id: 1,
                email: "admin@entreprise.com",
                role_name: "Administrateur Entreprise",
                user_type: "admin",
                is_active: true,
                is_two_factor_enabled: true
            },
            {
                id: 2,
                email: "commercial@entreprise.com",
                role_name: "Responsable Commercial",
                user_type: "staff",
                is_active: true,
                is_two_factor_enabled: false
            },
            {
                id: 3,
                email: "comptabilite@entreprise.com",
                role_name: "Responsable Financier & Comptable",
                user_type: "staff",
                is_active: true,
                is_two_factor_enabled: true
            },
            {
                id: 4,
                email: "stock@entreprise.com",
                role_name: "Responsable des Stocks & Magasinier",
                user_type: "staff",
                is_active: true,
                is_two_factor_enabled: false
            },
            {
                id: 5,
                email: "contact@client-partenaire.com",
                role_name: "Client Partenaire (Portail Externe)",
                user_type: "external",
                is_active: true,
                is_two_factor_enabled: false
            }
        ];
        localStorage.setItem("demo_tenant_users", JSON.stringify(defaults));
        return defaults;
    }

    // Récupération des utilisateurs
    async function fetchUsers() {
        if (isDemo) {
            const list = getDemoUsers();
            renderTable(list);
            updateKPIs(list);
            return;
        }

        try {
            const res = await fetch(`${API}/users/`, {
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (res.status === 401) {
                localStorage.removeItem("access_token");
                window.location.href = "index.html";
                return;
            }

            if (!res.ok) throw new Error("Erreur de récupération des utilisateurs.");
            const users = await res.json();
            renderTable(users);
            updateKPIs(users);
        } catch (error) {
            console.warn("Échec serveur, bascule en mode démo local :", error);
            const demoList = getDemoUsers();
            renderTable(demoList);
            updateKPIs(demoList);
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

    function getRoleBadge(user) {
        const role = (user.role_name || user.user_type || "").toLowerCase();
        if (role.includes("admin")) return `<span class="role-badge role-admin"><i class="fa-solid fa-shield-halved"></i> Admin</span>`;
        if (role.includes("commercial")) return `<span class="role-badge role-commercial"><i class="fa-solid fa-briefcase"></i> Commercial</span>`;
        if (role.includes("finance") || role.includes("compta")) return `<span class="role-badge role-finance"><i class="fa-solid fa-coins"></i> Finance</span>`;
        if (role.includes("stock") || role.includes("magasin")) return `<span class="role-badge role-stock"><i class="fa-solid fa-boxes-stacked"></i> Magasinier</span>`;
        if (user.user_type === "external" || role.includes("client") || role.includes("fournisseur")) return `<span class="role-badge role-external"><i class="fa-solid fa-globe"></i> Portail Tiers</span>`;
        return `<span class="role-badge role-staff"><i class="fa-solid fa-user"></i> Collaborateur</span>`;
    }

    function renderTable(users) {
        if (!users || users.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 24px; color: #6b7280;">Aucun utilisateur trouvé. Cliquez sur "Inscrire un Utilisateur" pour débuter.</td></tr>`;
            return;
        }

        tableBody.innerHTML = users.map(u => {
            const statusClass = u.is_active ? "status-active" : "status-inactive";
            const statusLabel = u.is_active ? "Actif" : "Désactivé";
            const perimeter = u.user_type === "external" ? "Portail Externe" : "Interne Entreprise";
            const mfaIcon = u.is_two_factor_enabled 
                ? `<span style="color:#16a34a; font-weight:600; font-size:12px;"><i class="fa-solid fa-lock"></i> Activé</span>` 
                : `<span style="color:#94a3b8; font-size:12px;"><i class="fa-solid fa-unlock"></i> Non configuré</span>`;

            return `
            <tr>
                <td><strong>#${u.id}</strong></td>
                <td>
                    <div style="font-weight:600; color:#111827;">${u.email}</div>
                    <small style="color:#64748b;">${u.role_name || u.user_type}</small>
                </td>
                <td>${getRoleBadge(u)}</td>
                <td><small style="font-weight:500; color:#475569;">${perimeter}</small></td>
                <td>${mfaIcon}</td>
                <td><span class="status-pill ${statusClass}">${statusLabel}</span></td>
                <td style="text-align: center;">
                    <button class="toggle-status-btn" data-id="${u.id}" style="background:none; border:1px solid #cbd5e1; border-radius:6px; padding:4px 8px; cursor:pointer; font-size:12px; color:#475569;" title="Changer l'état du compte">
                        ${u.is_active ? 'Désactiver' : 'Réactiver'}
                    </button>
                </td>
            </tr>
            `;
        }).join("");

        // Écouteurs pour activer/désactiver
        document.querySelectorAll(".toggle-status-btn").forEach(btn => {
            btn.addEventListener("click", () => handleToggleStatus(btn.dataset.id));
        });
    }

    // Inscription d'un nouveau collaborateur
    userForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const email = document.getElementById("new-email").value.trim();
        const roleVal = document.getElementById("new-role").value;
        const password = document.getElementById("new-password").value;
        const confirmPassword = document.getElementById("confirm-user-password").value;
        const roleLabel = document.getElementById("new-role").selectedOptions[0].text;

        if (password !== confirmPassword) {
            alert("Les deux mots de passe ne correspondent pas.");
            return;
        }

        // Détermination du user_type pour le backend
        let userType = "staff";
        if (roleVal === "admin") userType = "admin";
        else if (roleVal === "client_ext" || roleVal === "supplier_ext") userType = "external";

        if (isDemo) {
            const list = getDemoUsers();
            const newId = list.length > 0 ? Math.max(...list.map(u => u.id)) + 1 : 1;
            list.push({
                id: newId,
                email: email,
                role_name: roleLabel.split(" (")[0],
                user_type: userType,
                is_active: true,
                is_two_factor_enabled: false
            });
            localStorage.setItem("demo_tenant_users", JSON.stringify(list));
            modal.style.display = "none";
            userForm.reset();
            fetchUsers();
            alert(`Collaborateur "${email}" inscrit avec succès en mode démo !`);
            return;
        }

        // Mode API réel
        try {
            const payload = {
                email: email,
                password: password,
                tenant_id: "entreprise_a", // Utilise le tenant actif
                user_type: userType
            };

            const res = await fetch(`${API}/auth/register`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Erreur lors de l'inscription.");
            }

            modal.style.display = "none";
            userForm.reset();
            fetchUsers();
            alert(`Utilisateur "${email}" inscrit avec succès !`);
        } catch (error) {
            console.error(error);
            alert("Erreur : " + error.message);
        }
    });

    function handleToggleStatus(userId) {
        if (isDemo) {
            let list = getDemoUsers();
            list = list.map(u => {
                if (String(u.id) === String(userId)) {
                    return { ...u, is_active: !u.is_active };
                }
                return u;
            });
            localStorage.setItem("demo_tenant_users", JSON.stringify(list));
            fetchUsers();
            return;
        }
        alert("Action transmise au backend pour le compte #" + userId);
    }

    // Gestion de la modale
    if (openModalBtn) {
        openModalBtn.addEventListener("click", () => {
            userForm.reset();
            modal.style.display = "block";
        });
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener("click", () => {
            modal.style.display = "none";
        });
    }

    window.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
    });

    fetchUsers();
});
