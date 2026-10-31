document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    const tableBody = document.getElementById("clients-table-body");
    const modal = document.getElementById("client-modal");
    const openModalBtn = document.getElementById("open-client-modal");
    const closeModalBtn = document.getElementById("close-modal");
    const clientForm = document.getElementById("client-form");

    const kpiTotal = document.getElementById("kpi-total-clients");
    const kpiB2b = document.getElementById("kpi-b2b-count");
    const kpiB2c = document.getElementById("kpi-b2c-count");
    const kpiPortal = document.getElementById("kpi-portal-count");

    function getDemoClients() {
        const stored = localStorage.getItem("demo_clients");
        if (stored) return JSON.parse(stored);
        const defaults = [
            {
                id: 1,
                code: "CLI-001",
                name: "Société Commerciale Alpha",
                type: "B2B",
                tax_id: "1234567/A/M/000",
                email: "direction@alpha.com",
                phone: "+216 71 850 900",
                city: "Tunis",
                address: "Avenue Habib Bourguiba",
                portal_active: true
            },
            {
                id: 2,
                code: "CLI-002",
                name: "Cabinet Conseil Pro",
                type: "B2B",
                tax_id: "8765432/B/P/001",
                email: "contact@conseilpro.fr",
                phone: "+33 1 42 68 00 12",
                city: "Paris",
                address: "Boulevard Haussmann",
                portal_active: true
            },
            {
                id: 3,
                code: "CLI-003",
                name: "Groupe Industriel Moderne",
                type: "B2B",
                tax_id: "4598712/C/M/000",
                email: "achats@gim-group.com",
                phone: "+216 74 200 400",
                city: "Sfax",
                address: "Route de Gabès Km 3",
                portal_active: false
            },
            {
                id: 4,
                code: "CLI-004",
                name: "Ahmed Trabelsi",
                type: "B2C",
                tax_id: "-",
                email: "a.trabelsi@gmail.com",
                phone: "+216 98 123 456",
                city: "Sousse",
                address: "Cité Sahloul",
                portal_active: true
            }
        ];
        localStorage.setItem("demo_clients", JSON.stringify(defaults));
        return defaults;
    }

    function fetchClients() {
        const clients = getDemoClients();
        renderTable(clients);
        updateKPIs(clients);
    }

    function updateKPIs(list) {
        if (!list) return;
        const total = list.length;
        const b2b = list.filter(c => c.type === "B2B").length;
        const b2c = list.filter(c => c.type === "B2C").length;
        const portals = list.filter(c => c.portal_active).length;

        if (kpiTotal) kpiTotal.textContent = total;
        if (kpiB2b) kpiB2b.textContent = b2b;
        if (kpiB2c) kpiB2c.textContent = b2c;
        if (kpiPortal) kpiPortal.textContent = portals;
    }

    function renderTable(clients) {
        if (!clients || clients.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 24px; color: #6b7280;">Aucun client enregistré. Cliquez sur "Nouveau Client" pour en créer un.</td></tr>`;
            return;
        }

        tableBody.innerHTML = clients.map(c => {
            const badgeType = c.type === "B2B" ? "badge-b2b" : "badge-b2c";
            const portalStatus = c.portal_active 
                ? `<span style="color:#16a34a; font-weight:600; font-size:12px;"><i class="fa-solid fa-circle-check"></i> Actif</span>`
                : `<span style="color:#94a3b8; font-size:12px;"><i class="fa-solid fa-circle-xmark"></i> Inactif</span>`;

            return `
            <tr>
                <td><strong>${c.code}</strong></td>
                <td>
                    <div style="font-weight:600; color:#111827;">${c.name}</div>
                    <small style="color:#64748b;">${c.tax_id && c.tax_id !== '-' ? 'MF: ' + c.tax_id : 'Client Particulier'}</small>
                </td>
                <td><span class="client-badge ${badgeType}">${c.type}</span></td>
                <td>
                    <div><a href="mailto:${c.email}" style="color:#1a73e8; text-decoration:none; font-size:13px;">${c.email}</a></div>
                    <small style="color:#64748b;">${c.phone || '-'}</small>
                </td>
                <td>
                    <div style="font-weight:500; font-size:13px;">${c.city || '—'}</div>
                    <small style="color:#64748b;">${c.address || ''}</small>
                </td>
                <td>${portalStatus}</td>
                <td style="text-align: center;">
                    <button class="btn-action-small create-inv-btn" data-name="${encodeURIComponent(c.name)}" title="Émettre une facture pour ce client">
                        <i class="fa-solid fa-file-invoice" style="color:#1a73e8;"></i> Facturer
                    </button>
                    <button class="btn-action-small delete-client-btn" data-id="${c.id}" style="color:#dc2626; border-color:#fecaca; margin-left:4px;" title="Supprimer ce client">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            </tr>
            `;
        }).join("");

        // Écouteurs pour facturer directement
        document.querySelectorAll(".create-inv-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const clientName = decodeURIComponent(btn.dataset.name);
                localStorage.setItem("prefill_invoice_customer", clientName);
                window.location.href = "factures.html";
            });
        });

        // Écouteurs pour supprimer
        document.querySelectorAll(".delete-client-btn").forEach(btn => {
            btn.addEventListener("click", () => handleDeleteClient(btn.dataset.id));
        });
    }

    // Enregistrement d'un nouveau client
    clientForm.addEventListener("submit", (e) => {
        e.preventDefault();

        const type = document.getElementById("client-type").value;
        const taxId = document.getElementById("client-tax-id").value.trim() || "-";
        const name = document.getElementById("client-name").value.trim();
        const email = document.getElementById("client-email").value.trim();
        const phone = document.getElementById("client-phone").value.trim();
        const city = document.getElementById("client-city").value.trim();
        const address = document.getElementById("client-address").value.trim();
        const hasPortal = document.getElementById("client-portal-access").checked;

        const list = getDemoClients();
        const newId = list.length > 0 ? Math.max(...list.map(c => c.id)) + 1 : 1;
        const newClient = {
            id: newId,
            code: `CLI-${String(newId).padStart(3, '0')}`,
            name: name,
            type: type,
            tax_id: taxId,
            email: email,
            phone: phone,
            city: city,
            address: address,
            portal_active: hasPortal
        };

        list.unshift(newClient);
        localStorage.setItem("demo_clients", JSON.stringify(list));

        // Si l'accès portail client est activé, créer automatiquement l'utilisateur externe
        if (hasPortal) {
            let tenantUsers = JSON.parse(localStorage.getItem("demo_tenant_users") || "[]");
            const existingUser = tenantUsers.find(u => u.email === email);
            if (!existingUser) {
                tenantUsers.push({
                    id: tenantUsers.length + 1,
                    email: email,
                    role_name: `Portail Client (${name})`,
                    user_type: "external",
                    is_active: true,
                    is_two_factor_enabled: false
                });
                localStorage.setItem("demo_tenant_users", JSON.stringify(tenantUsers));
            }
        }

        modal.style.display = "none";
        clientForm.reset();
        fetchClients();
        alert(`Client "${name}" enregistré avec succès !`);
    });

    function handleDeleteClient(clientId) {
        if (!confirm("Voulez-vous vraiment supprimer ce client ?")) return;
        let list = getDemoClients();
        list = list.filter(c => String(c.id) !== String(clientId));
        localStorage.setItem("demo_clients", JSON.stringify(list));
        fetchClients();
    }

    // Gestion de la modale
    if (openModalBtn) {
        openModalBtn.addEventListener("click", () => {
            clientForm.reset();
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

    fetchClients();
});
