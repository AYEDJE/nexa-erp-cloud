document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    const tr = (k, p) => (window.i18n ? window.i18n.t(k, p) : k);
    const money = (n) => (window.i18n ? window.i18n.fmtMoney(n) : Number(n || 0).toFixed(2) + " €");

    const tableBody = document.getElementById("invoices-table-body");
    const modal = document.getElementById("invoice-modal");
    const openModalBtn = document.getElementById("open-invoice-modal");
    const closeModalBtn = document.getElementById("close-modal");
    const invoiceForm = document.getElementById("invoice-form");

    const kpiTotalTtc = document.getElementById("kpi-total-ttc");
    const kpiCountPayees = document.getElementById("kpi-count-payees");
    const kpiCountAttente = document.getElementById("kpi-count-attente");

    const isDemo = !token || token.startsWith("demo_");
    let currentInvoices = [];

    const DOC_LABELS = {
        INVOICE: "Facture",
        QUOTE: "Devis",
        PROFORMA: "Proforma",
        DELIVERY_NOTE: "Bon de livraison",
        CREDIT_NOTE: "Avoir"
    };
    const LEGACY_DOC_TYPES = { FACTURE: "INVOICE", DEVIS: "QUOTE", COMMANDE: "PROFORMA" };
    const normDocType = (t) => LEGACY_DOC_TYPES[t] || t || "INVOICE";

    const ISSUER_FIELDS = {
        name: "issuer-name",
        tax_id: "issuer-tax-id",
        address: "issuer-address",
        phone: "issuer-phone",
        email: "issuer-email",
        issuing_place: "issuer-place"
    };

    /* =========================================================================
       GESTION DES DONNÉES PAR ENTREPRISE (MULTI-TENANT)
       ========================================================================= */

    function getTenantInvoices() {
        if (window.NexaTenant) {
            return window.NexaTenant.getData("invoices", []);
        }
        try {
            return JSON.parse(localStorage.getItem("demo_invoices")) || [];
        } catch (_) {
            return [];
        }
    }

    function saveTenantInvoices(list) {
        if (window.NexaTenant) {
            window.NexaTenant.setData("invoices", list);
        } else {
            localStorage.setItem("demo_invoices", JSON.stringify(list));
        }
    }

    function loadCompanyProfile() {
        if (window.NexaTenant) {
            const p = window.NexaTenant.getData("company", null);
            if (p && Object.keys(p).length > 0) return p;
            const u = window.NexaTenant.getCurrentUser();
            return {
                name: (u && (u.company_name || u.company)) || "Mon Entreprise ERP",
                address: "Avenue Habib Bourguiba",
                city: "Tunis",
                country: "Tunisie",
                phone: "+216 71 000 000",
                email: (u && u.email) || "contact@entreprise.tn",
                tax_id: "1234567/A/M/000",
                issuing_place: "Tunis"
            };
        }
        try { return JSON.parse(localStorage.getItem("company_profile")) || {}; } catch (_) { return {}; }
    }

    function fillIssuerForm() {
        const p = loadCompanyProfile();
        Object.entries(ISSUER_FIELDS).forEach(([key, id]) => {
            const el = document.getElementById(id);
            if (el) el.value = p[key] || "";
        });
    }

    function readIssuerForm() {
        const issuer = {};
        Object.entries(ISSUER_FIELDS).forEach(([key, id]) => {
            issuer[key] = (document.getElementById(id)?.value || "").trim();
        });
        return issuer;
    }

    /* =========================================================================
       AUTO-COMPLÉTION DYNAMIQUE (CLIENTS & PRODUITS DU TENANT)
       ========================================================================= */

    function populateDatalists() {
        // 1. Datalist Clients
        const clientDatalist = document.getElementById("clients-datalist");
        const clientInput = document.getElementById("customer-name");
        const clientEmailInput = document.getElementById("customer-email");
        const clientPhoneInput = document.getElementById("customer-phone");
        const clientAddressInput = document.getElementById("customer-address");

        const tenantClients = window.NexaTenant ? window.NexaTenant.getData("clients", []) : [];
        if (clientDatalist) {
            clientDatalist.innerHTML = tenantClients.map(c => 
                `<option value="${escapeHtml(c.name)}">${escapeHtml(c.name)} - ${escapeHtml(c.phone || c.email || '')}</option>`
            ).join("");
        }

        if (clientInput && !clientInput.dataset.bound) {
            clientInput.dataset.bound = "true";
            clientInput.addEventListener("input", () => {
                const val = clientInput.value.trim().toLowerCase();
                const matched = tenantClients.find(c => (c.name || "").toLowerCase() === val);
                if (matched) {
                    if (clientEmailInput && matched.email) clientEmailInput.value = matched.email;
                    if (clientPhoneInput && matched.phone) clientPhoneInput.value = matched.phone;
                    if (clientAddressInput && (matched.address || matched.city)) {
                        clientAddressInput.value = [matched.address, matched.city].filter(Boolean).join(", ");
                    }
                }
            });
        }

        // 2. Datalist Produits
        const productDatalist = document.getElementById("products-datalist");
        const itemInput = document.getElementById("item-name");
        const itemPriceInput = document.getElementById("item-price");
        const itemTvaInput = document.getElementById("item-tva");

        const tenantProducts = window.NexaTenant ? window.NexaTenant.getData("products", []) : [];
        if (productDatalist) {
            productDatalist.innerHTML = tenantProducts.map(p => 
                `<option value="${escapeHtml(p.name)}">${escapeHtml(p.name)} | ${p.price || 0} € (Stock: ${p.stock ?? 0})</option>`
            ).join("");
        }

        if (itemInput && !itemInput.dataset.bound) {
            itemInput.dataset.bound = "true";
            itemInput.addEventListener("input", () => {
                const val = itemInput.value.trim().toLowerCase();
                const matched = tenantProducts.find(p => (p.name || "").toLowerCase() === val);
                if (matched) {
                    if (itemPriceInput && matched.price !== undefined) {
                        itemPriceInput.value = matched.price;
                    }
                    if (itemTvaInput && matched.tva_rate !== undefined) {
                        itemTvaInput.value = matched.tva_rate;
                    }
                }
            });
        }
    }

    function formatApiError(data, fallback) {
        if (!data) return fallback;
        const d = data.detail !== undefined ? data.detail
                : data.message !== undefined ? data.message
                : data;
        if (typeof d === "string") return d;
        if (Array.isArray(d)) {
            return d.map(e => {
                if (typeof e === "string") return e;
                const field = Array.isArray(e.loc)
                    ? e.loc.filter(x => x !== "body" && x !== "query").join(" → ")
                    : "";
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

    function redirectIfUnauthorized(res) {
        if (res.status === 401) {
            localStorage.removeItem("access_token");
            window.location.href = "index.html";
            return true;
        }
        return false;
    }

    /* =========================================================================
       CHARGEMENT ET AFFICHAGE DES FACTURES
       ========================================================================= */

    async function fetchInvoices() {
        if (isDemo) {
            const list = getTenantInvoices();
            renderTable(list);
            updateKPIs(list);
            return;
        }

        try {
            const response = await fetch(`${API}/invoices/`, {
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (redirectIfUnauthorized(response)) return;

            if (!response.ok) {
                const errData = await response.json().catch(() => null);
                throw new Error(formatApiError(errData, `Erreur ${response.status}`));
            }
            const invoices = await response.json();
            renderTable(invoices);
            updateKPIs(invoices);
        } catch (error) {
            console.warn("Backend indisponible, utilisation du registre isolé local :", error);
            const list = getTenantInvoices();
            renderTable(list);
            updateKPIs(list);
        }
    }

    function updateKPIs(list) {
        if (!list) return;
        const total = list.reduce((sum, inv) => sum + (parseFloat(inv.total_ttc) || 0), 0);
        const payees = list.filter(inv => inv.status === "paid").length;
        const attente = list.filter(inv => inv.status === "pending" || inv.status === "draft").length;

        if (kpiTotalTtc) kpiTotalTtc.textContent = money(total);
        if (kpiCountPayees) kpiCountPayees.textContent = payees;
        if (kpiCountAttente) kpiCountAttente.textContent = attente;
    }

    function renderTable(invoices) {
        currentInvoices = invoices || [];
        if (!invoices || invoices.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 28px; color: #64748b;">
                <i class="fa-solid fa-folder-open" style="font-size: 24px; color:#cbd5e1; display:block; margin-bottom:8px;"></i>
                Aucun document commercial enregistré pour cette entreprise.<br>
                <small style="color:#94a3b8;">Cliquez sur <strong>"Nouvelle Facture"</strong> pour émettre votre première facture ou devis.</small>
            </td></tr>`;
            return;
        }

        tableBody.innerHTML = invoices.map(inv => {
            let statusClass = "status-draft";
            let statusLabel = "Brouillon";
            if (inv.status === "paid") {
                statusClass = "status-paid";
                statusLabel = "Payée";
            } else if (inv.status === "pending") {
                statusClass = "status-pending";
                statusLabel = "En attente";
            }

            const dt = normDocType(inv.doc_type);
            const docBadge = dt === "QUOTE" ? "background:#f3e8ff; color:#7e22ce;"
                           : dt === "CREDIT_NOTE" ? "background:#fee2e2; color:#991b1b;"
                           : "background:#e0f2fe; color:#0369a1;";

            return `
            <tr>
                <td><strong>${escapeHtml(inv.number)}</strong></td>
                <td><span style="padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; ${docBadge}">${escapeHtml(DOC_LABELS[dt] || dt)}</span></td>
                <td><strong>${escapeHtml(inv.customer_name) || "Client anonyme"}</strong></td>
                <td>${money(inv.total_ht)}</td>
                <td><strong style="color:#111827;">${money(inv.total_ttc)}</strong></td>
                <td><span class="status-pill ${statusClass}">${statusLabel}</span></td>
                <td style="text-align: center; white-space: nowrap;">
                    ${canPay(inv) ? `<button class="btn-action pay" data-id="${inv.id}" title="Enregistrer le paiement" style="color:#166534; border-color:#bbf7d0; background:#f0fdf4;">
                        <i class="fa-solid fa-money-bill-wave"></i> Régler
                    </button>` : ""}
                    <button class="btn-action pdf" data-id="${inv.id}" data-number="${escapeHtml(inv.number)}" title="Imprimer ou Télécharger en PDF">
                        <i class="fa-solid fa-file-pdf"></i> PDF
                    </button>
                    <button class="btn-action word" data-id="${inv.id}" data-number="${escapeHtml(inv.number)}" title="Télécharger le document officiel Word (.doc)">
                        <i class="fa-solid fa-file-word"></i> Word
                    </button>
                </td>
            </tr>
            `;
        }).join("");

        document.querySelectorAll(".btn-action.pay").forEach(btn => {
            btn.addEventListener("click", () => openPayModal(btn.dataset.id));
        });

        document.querySelectorAll(".btn-action.pdf").forEach(btn => {
            btn.addEventListener("click", () => handleDownloadPDF(btn.dataset.id, btn.dataset.number));
        });

        document.querySelectorAll(".btn-action.word").forEach(btn => {
            btn.addEventListener("click", () => handleDownloadWord(btn.dataset.id, btn.dataset.number));
        });
    }

    /* =========================================================================
       GÉNÉRATION ET TÉLÉCHARGEMENT PDF & WORD
       ========================================================================= */

    function convertirNombreEnLettres(montant) {
        const unites = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"];
        const dizaines = ["", "", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante-dix", "quatre-vingts", "quatre-vingt-dix"];

        function nbVersLettres(n) {
            if (n === 0) return "zéro";
            if (n < 20) return unites[n];
            if (n < 100) {
                const d = Math.floor(n / 10);
                const r = n % 10;
                if (d === 7 || d === 9) {
                    return dizaines[d - 1] + (r === 1 ? "-et-onze" : "-" + unites[10 + r]);
                }
                return dizaines[d] + (r === 1 ? "-et-un" : (r > 0 ? "-" + unites[r] : ""));
            }
            if (n < 1000) {
                const c = Math.floor(n / 100);
                const r = n % 100;
                const centStr = c === 1 ? "cent" : unites[c] + " cents";
                return centStr + (r > 0 ? " " + nbVersLettres(r) : "");
            }
            if (n < 1000000) {
                const m = Math.floor(n / 1000);
                const r = n % 1000;
                const milleStr = m === 1 ? "mille" : nbVersLettres(m) + " mille";
                return milleStr + (r > 0 ? " " + nbVersLettres(r) : "");
            }
            return n.toLocaleString("fr-FR");
        }

        const total = Math.max(0, parseFloat(montant) || 0);
        const entier = Math.floor(total);
        const centimes = Math.round((total - entier) * 100);

        let texte = nbVersLettres(entier) + " dinars / euros";
        if (centimes > 0) {
            texte += " et " + nbVersLettres(centimes) + " centimes";
        }
        return texte.charAt(0).toUpperCase() + texte.slice(1);
    }

    async function handleDownloadPDF(invoiceId, invoiceNumber) {
        const inv = currentInvoices.find(i => String(i.id) === String(invoiceId));
        if (!inv) return;

        // Si le backend est actif et hors mode démo
        if (!isDemo && window.API) {
            try {
                const res = await fetch(`${API}/invoices/${invoiceId}/pdf`, {
                    headers: { "Authorization": `Bearer ${token}` }
                });
                if (res.ok) {
                    const blob = await res.blob();
                    const downloadUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = downloadUrl;
                    a.download = `Facture_${invoiceNumber || invoiceId}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(downloadUrl);
                    return;
                }
            } catch (_) {}
        }

        // Mode Local / Hors-ligne : Génération du document officiel PDF avec aperçu et impression directe
        const company = (inv.issuer && inv.issuer.name) ? inv.issuer : loadCompanyProfile();
        const docTypeLabel = DOC_LABELS[normDocType(inv.doc_type)] || "Facture";
        const totalEnLettres = convertirNombreEnLettres(inv.total_ttc);

        const itemsHtml = (inv.items && inv.items.length > 0) 
            ? inv.items.map((it, idx) => `
                <tr>
                    <td style="padding:10px; border-bottom:1px solid #e2e8f0; text-align:center;">${idx + 1}</td>
                    <td style="padding:10px; border-bottom:1px solid #e2e8f0;"><strong>${escapeHtml(it.product_name)}</strong></td>
                    <td style="padding:10px; border-bottom:1px solid #e2e8f0; text-align:center;">${it.quantity}</td>
                    <td style="padding:10px; border-bottom:1px solid #e2e8f0; text-align:right;">${money(it.unit_price_ht)}</td>
                    <td style="padding:10px; border-bottom:1px solid #e2e8f0; text-align:center;">${it.tva_rate || 19}%</td>
                    <td style="padding:10px; border-bottom:1px solid #e2e8f0; text-align:right; font-weight:600;">${money((it.quantity * it.unit_price_ht))}</td>
                </tr>
            `).join("")
            : `
                <tr>
                    <td style="padding:10px; border-bottom:1px solid #e2e8f0; text-align:center;">1</td>
                    <td style="padding:10px; border-bottom:1px solid #e2e8f0;">Prestation commerciale / Vente de produits</td>
                    <td style="padding:10px; border-bottom:1px solid #e2e8f0; text-align:center;">1</td>
                    <td style="padding:10px; border-bottom:1px solid #e2e8f0; text-align:right;">${money(inv.total_ht)}</td>
                    <td style="padding:10px; border-bottom:1px solid #e2e8f0; text-align:center;">19%</td>
                    <td style="padding:10px; border-bottom:1px solid #e2e8f0; text-align:right; font-weight:600;">${money(inv.total_ht)}</td>
                </tr>
            `;

        const printWindow = window.open("", "_blank", "width=850,height=900");
        if (!printWindow) {
            alert("Veuillez autoriser les popups dans votre navigateur pour afficher et imprimer le document.");
            return;
        }

        printWindow.document.write(`
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <title>${docTypeLabel} — ${inv.number}</title>
            <style>
                @page { size: A4; margin: 15mm; }
                body { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; color: #1e293b; background: #fff; margin: 0; padding: 20px; font-size: 13px; line-height: 1.5; }
                .top-actions { background: #0f172a; color: #fff; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; border-radius: 6px; margin-bottom: 25px; }
                .top-actions button { background: #2563eb; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; font-weight: 600; cursor: pointer; }
                .top-actions button:hover { background: #1d4ed8; }
                @media print {
                    .top-actions { display: none !important; }
                    body { padding: 0 !important; }
                }
                .invoice-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 30px; border-bottom: 2px solid #1a73e8; padding-bottom: 20px; }
                .company-info h2 { margin: 0 0 6px 0; color: #1a73e8; font-size: 22px; font-weight: 700; }
                .doc-meta { text-align: right; }
                .doc-meta h1 { margin: 0 0 6px 0; color: #0f172a; font-size: 22px; text-transform: uppercase; letter-spacing: 1px; }
                .doc-meta .badge { display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: 700; font-size: 12px; background: ${inv.status === 'paid' ? '#dcfce7; color:#166534;' : '#fef9c3; color:#854d0e;'}; }
                .parties-box { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px; }
                .party-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 15px; }
                .party-card h4 { margin: 0 0 8px 0; font-size: 12px; text-transform: uppercase; color: #64748b; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; }
                table.items-table { width: 100%; border-collapse: collapse; margin-bottom: 25px; }
                table.items-table th { background: #f1f5f9; color: #334155; font-weight: 700; text-align: left; padding: 10px; border-bottom: 2px solid #cbd5e1; }
                .totals-section { display: flex; justify-content: flex-end; margin-bottom: 30px; }
                .totals-table { width: 320px; border-collapse: collapse; }
                .totals-table td { padding: 6px 10px; border-bottom: 1px solid #e2e8f0; }
                .totals-table tr.total-row td { background: #eff6ff; font-weight: 800; font-size: 15px; color: #1a73e8; border-top: 2px solid #1a73e8; }
                .words-box { background: #f8fafc; border-left: 4px solid #1a73e8; padding: 12px; margin-bottom: 30px; font-size: 12px; color: #334155; }
                .footer-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; align-items: flex-end; margin-top: 40px; }
                .stamp-box { border: 1px dashed #94a3b8; height: 110px; border-radius: 6px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #94a3b8; font-size: 11px; text-align: center; }
            </style>
        </head>
        <body>
            <div class="top-actions">
                <span>Document officiel généré par <strong>NEXA ERP Cloud</strong></span>
                <div>
                    <button onclick="window.print()">🖨️ Imprimer / Enregistrer en PDF</button>
                    <button onclick="window.close()" style="background:#64748b; margin-left:6px;">Fermer</button>
                </div>
            </div>

            <div class="invoice-header">
                <div class="company-info">
                    <h2>${escapeHtml(company.name || "NEXA ERP Cloud")}</h2>
                    <div>${escapeHtml(company.address || "")}</div>
                    <div>${escapeHtml(company.city || "Tunis")}, ${escapeHtml(company.country || "Tunisie")}</div>
                    <div>Tél : ${escapeHtml(company.phone || "+216 71 000 000")} | Email : ${escapeHtml(company.email || "")}</div>
                    <div>Matricule Fiscal : <strong>${escapeHtml(company.tax_id || "1234567/A/M/000")}</strong></div>
                </div>
                <div class="doc-meta">
                    <h1>${docTypeLabel}</h1>
                    <div style="font-size:14px; font-weight:700; color:#1a73e8; margin-bottom:4px;">N° ${escapeHtml(inv.number)}</div>
                    <div style="color:#64748b; font-size:12px; margin-bottom:6px;">Date d'émission : ${new Date(inv.created_at || Date.now()).toLocaleDateString("fr-FR")}</div>
                    <span class="badge">${inv.status === 'paid' ? 'PAYÉE' : 'EN ATTENTE'}</span>
                </div>
            </div>

            <div class="parties-box">
                <div class="party-card">
                    <h4>Émetteur</h4>
                    <strong style="font-size:14px; color:#0f172a;">${escapeHtml(company.name || "Nexa ERP")}</strong><br>
                    ${escapeHtml(company.address || "")}<br>
                    ${escapeHtml(company.phone || "")}<br>
                    Lieu d'émission : ${escapeHtml(company.issuing_place || "Tunis")}
                </div>
                <div class="party-card">
                    <h4>Facturé à (Client)</h4>
                    <strong style="font-size:14px; color:#0f172a;">${escapeHtml(inv.customer_name || "Client Partenaire")}</strong><br>
                    ${escapeHtml(inv.customer_address || "Siège social client")}<br>
                    Tél : ${escapeHtml(inv.customer_phone || "Non renseigné")}<br>
                    Email : ${escapeHtml(inv.customer_email || "Non renseigné")}
                </div>
            </div>

            <table class="items-table">
                <thead>
                    <tr>
                        <th style="width:40px; text-align:center;">#</th>
                        <th>Désignation de la prestation / article</th>
                        <th style="width:70px; text-align:center;">Qté</th>
                        <th style="width:110px; text-align:right;">Prix Unit. HT</th>
                        <th style="width:70px; text-align:center;">TVA</th>
                        <th style="width:120px; text-align:right;">Total HT</th>
                    </tr>
                </thead>
                <tbody>
                    ${itemsHtml}
                </tbody>
            </table>

            <div class="totals-section">
                <table class="totals-table">
                    <tr>
                        <td style="color:#64748b;">Total Net HT :</td>
                        <td style="text-align:right; font-weight:600;">${money(inv.total_ht)}</td>
                    </tr>
                    <tr>
                        <td style="color:#64748b;">Total TVA :</td>
                        <td style="text-align:right; font-weight:600;">${money(inv.tax_amount)}</td>
                    </tr>
                    <tr class="total-row">
                        <td>TOTAL NET TTC :</td>
                        <td style="text-align:right;">${money(inv.total_ttc)}</td>
                    </tr>
                </table>
            </div>

            <div class="words-box">
                Arrêtée la présente facture à la somme TTC de :<br>
                <strong style="font-size:13px; color:#1e293b;">${totalEnLettres}</strong>
            </div>

            <div class="footer-grid">
                <div style="font-size:11px; color:#64748b;">
                    <strong>Conditions de règlement :</strong> ${escapeHtml(inv.payment_terms || "Paiement à 30 jours")}<br>
                    Document officiel généré électroniquement sous le standard sécurisé NEXA ERP Multi-Tenant.<br>
                    Code d'authenticité électronique : <code>NEXA-${(inv.id || 1).toString().padStart(6, '0')}-${Date.now().toString(36).toUpperCase()}</code>
                </div>
                <div class="stamp-box">
                    <strong>Cachet & Signature</strong><br>
                    <em>${escapeHtml(company.name || "Nexa ERP")}</em>
                </div>
            </div>
        </body>
        </html>
        `);
        printWindow.document.close();
        setTimeout(() => {
            printWindow.focus();
            printWindow.print();
        }, 500);
    }

    function handleDownloadWord(invoiceId, invoiceNumber) {
        const inv = currentInvoices.find(i => String(i.id) === String(invoiceId));
        if (!inv) return;

        const company = (inv.issuer && inv.issuer.name) ? inv.issuer : loadCompanyProfile();
        const docTypeLabel = DOC_LABELS[normDocType(inv.doc_type)] || "Facture";
        const totalEnLettres = convertirNombreEnLettres(inv.total_ttc);

        const itemsRows = (inv.items && inv.items.length > 0)
            ? inv.items.map((it, idx) => `
                <tr>
                    <td style="padding: 8px; border: 1px solid #d1d5db; text-align: center;">${idx + 1}</td>
                    <td style="padding: 8px; border: 1px solid #d1d5db;">${escapeHtml(it.product_name)}</td>
                    <td style="padding: 8px; border: 1px solid #d1d5db; text-align: center;">${it.quantity}</td>
                    <td style="padding: 8px; border: 1px solid #d1d5db; text-align: right;">${money(it.unit_price_ht)}</td>
                    <td style="padding: 8px; border: 1px solid #d1d5db; text-align: center;">${it.tva_rate || 19}%</td>
                    <td style="padding: 8px; border: 1px solid #d1d5db; text-align: right; font-weight: bold;">${money(it.quantity * it.unit_price_ht)}</td>
                </tr>
            `).join("")
            : `
                <tr>
                    <td style="padding: 8px; border: 1px solid #d1d5db; text-align: center;">1</td>
                    <td style="padding: 8px; border: 1px solid #d1d5db;">Prestation commerciale / Vente de produits</td>
                    <td style="padding: 8px; border: 1px solid #d1d5db; text-align: center;">1</td>
                    <td style="padding: 8px; border: 1px solid #d1d5db; text-align: right;">${money(inv.total_ht)}</td>
                    <td style="padding: 8px; border: 1px solid #d1d5db; text-align: center;">19%</td>
                    <td style="padding: 8px; border: 1px solid #d1d5db; text-align: right; font-weight: bold;">${money(inv.total_ht)}</td>
                </tr>
            `;

        const wordHtml = `
        <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
        <head>
            <meta charset='utf-8'>
            <title>${docTypeLabel} - ${inv.number}</title>
            <style>
                body { font-family: 'Calibri', 'Segoe UI', Arial, sans-serif; font-size: 11pt; color: #1e293b; margin: 20mm; }
                h1 { color: #1a73e8; font-size: 20pt; margin-bottom: 5px; }
                h2 { color: #0f172a; font-size: 16pt; margin: 0; }
                table { width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 15px; }
                th { background-color: #1a73e8; color: #ffffff; padding: 10px; font-weight: bold; border: 1px solid #1a73e8; }
                .party-table td { border: none; padding: 8px; vertical-align: top; }
                .party-box { background-color: #f8fafc; border: 1px solid #cbd5e1; padding: 12px; }
                .total-table { width: 45%; margin-left: auto; border: 1px solid #cbd5e1; }
                .total-table td { padding: 8px 12px; border: 1px solid #e2e8f0; }
                .total-ttc { background-color: #eff6ff; font-weight: bold; font-size: 13pt; color: #1a73e8; border-top: 2px solid #1a73e8; }
                .stamp-zone { margin-top: 40px; border: 1px dashed #94a3b8; padding: 25px; width: 45%; text-align: center; color: #64748b; margin-left: auto; }
            </style>
        </head>
        <body>
            <table class="party-table" style="margin-bottom: 25px;">
                <tr>
                    <td style="width: 55%;">
                        <h1>${escapeHtml(company.name || "NEXA ERP Cloud")}</h1>
                        <div>${escapeHtml(company.address || "")}</div>
                        <div>${escapeHtml(company.city || "Tunis")}, ${escapeHtml(company.country || "Tunisie")}</div>
                        <div>Tél : ${escapeHtml(company.phone || "")}</div>
                        <div>Email : ${escapeHtml(company.email || "")}</div>
                        <div>Matricule Fiscal : <strong>${escapeHtml(company.tax_id || "1234567/A/M/000")}</strong></div>
                    </td>
                    <td style="width: 45%; text-align: right;">
                        <h2>${docTypeLabel.toUpperCase()}</h2>
                        <div style="font-size: 14pt; font-weight: bold; color: #1a73e8; margin-top: 5px;">N° ${escapeHtml(inv.number)}</div>
                        <div style="color: #64748b; margin-top: 4px;">Date : ${new Date(inv.created_at || Date.now()).toLocaleDateString("fr-FR")}</div>
                        <div style="margin-top: 6px;">Statut : <strong>${inv.status === 'paid' ? 'PAYÉE' : 'EN ATTENTE'}</strong></div>
                    </td>
                </tr>
            </table>

            <table class="party-table" style="margin-bottom: 25px;">
                <tr>
                    <td style="width: 50%;">
                        <div class="party-box">
                            <strong style="color: #64748b; font-size: 10pt; text-transform: uppercase;">Émetteur</strong><br>
                            <strong>${escapeHtml(company.name || "Nexa ERP")}</strong><br>
                            ${escapeHtml(company.address || "")}<br>
                            Lieu : ${escapeHtml(company.issuing_place || "Tunis")}
                        </div>
                    </td>
                    <td style="width: 50%;">
                        <div class="party-box">
                            <strong style="color: #64748b; font-size: 10pt; text-transform: uppercase;">Client Facturé</strong><br>
                            <strong>${escapeHtml(inv.customer_name || "Client Partenaire")}</strong><br>
                            ${escapeHtml(inv.customer_address || "Siège social client")}<br>
                            Tél : ${escapeHtml(inv.customer_phone || "")}<br>
                            Email : ${escapeHtml(inv.customer_email || "")}
                        </div>
                    </td>
                </tr>
            </table>

            <table>
                <thead>
                    <tr>
                        <th style="width: 5%; text-align: center;">#</th>
                        <th style="width: 45%; text-align: left;">Désignation</th>
                        <th style="width: 10%; text-align: center;">Qté</th>
                        <th style="width: 15%; text-align: right;">Prix Unit. HT</th>
                        <th style="width: 10%; text-align: center;">TVA</th>
                        <th style="width: 15%; text-align: right;">Total HT</th>
                    </tr>
                </thead>
                <tbody>
                    ${itemsRows}
                </tbody>
            </table>

            <table class="total-table">
                <tr>
                    <td>Total Net HT :</td>
                    <td style="text-align: right; font-weight: bold;">${money(inv.total_ht)}</td>
                </tr>
                <tr>
                    <td>Total TVA :</td>
                    <td style="text-align: right; font-weight: bold;">${money(inv.tax_amount)}</td>
                </tr>
                <tr class="total-ttc">
                    <td>TOTAL NET TTC :</td>
                    <td style="text-align: right;">${money(inv.total_ttc)}</td>
                </tr>
            </table>

            <div style="background-color: #f8fafc; border-left: 4px solid #1a73e8; padding: 12px; margin-top: 20px; font-size: 10.5pt;">
                Arrêtée la présente ${docTypeLabel.toLowerCase()} à la somme de :<br>
                <strong>${totalEnLettres}</strong>
            </div>

            <div style="margin-top: 20px; font-size: 10pt; color: #475569;">
                <strong>Conditions de paiement :</strong> ${escapeHtml(inv.payment_terms || "Paiement à 30 jours")}<br>
                Document certifié conforme issu de NEXA ERP Cloud (Environnement Entreprise Sécurisé).
            </div>

            <div class="stamp-zone">
                <strong>Cachet commercial & Signature</strong><br><br><br>
                <em>${escapeHtml(company.name || "Nexa ERP")}</em>
            </div>
        </body>
        </html>
        `;

        const blob = new Blob(['\ufeff', wordHtml], { type: 'application/msword;charset=utf-8' });
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = `${docTypeLabel}_${invoiceNumber || invoiceId}.doc`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);
    }

    /* =========================================================================
       CRÉATION D'UNE NOUVELLE FACTURE OU DEVIS
       ========================================================================= */

    if (openModalBtn) {
        openModalBtn.addEventListener("click", () => {
            invoiceForm.reset();
            fillIssuerForm();
            populateDatalists();
            modal.style.display = "block";
        });
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener("click", () => { modal.style.display = "none"; });
    }

    window.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
    });

    invoiceForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const submitBtn = invoiceForm.querySelector("button[type='submit']");
        const docType = document.getElementById("doc-type").value;
        const lang = document.getElementById("inv-lang").value;
        const customerName = document.getElementById("customer-name").value.trim();
        const customerEmail = document.getElementById("customer-email").value.trim();
        const customerPhone = document.getElementById("customer-phone").value.trim();
        const customerAddress = (document.getElementById("customer-address")?.value || "").trim();
        const issuer = readIssuerForm();
        const itemName = document.getElementById("item-name").value.trim();
        const itemQty = parseFloat(document.getElementById("item-qty").value) || 1;
        const itemPrice = parseFloat(document.getElementById("item-price").value) || 0;
        const rawTva = parseFloat(document.getElementById("item-tva").value);
        const itemTva = Number.isNaN(rawTva) ? 19.0 : rawTva;
        const paymentTerms = document.getElementById("payment-terms").value.trim();

        const lineHt = itemQty * itemPrice;
        const lineTva = lineHt * (itemTva / 100.0);
        const lineTtc = lineHt + lineTva;

        // Mémoriser l'émetteur pour la prochaine fois
        if (window.NexaTenant) {
            window.NexaTenant.setData("company", { ...loadCompanyProfile(), ...issuer });
        }

        // Mode Local / Hors-ligne / Démo
        if (isDemo || !window.API) {
            const list = getTenantInvoices();
            const newId = list.length > 0 ? Math.max(...list.map(i => i.id || 0)) + 1 : 1;
            const prefix = docType === "QUOTE" ? "DEV" : docType === "DELIVERY_NOTE" ? "BL" : "FAC";
            const currentYearMonth = new Date().toISOString().slice(0, 7).replace("-", "");
            
            const newInv = {
                id: newId,
                number: `${prefix}-${currentYearMonth}-${newId.toString().padStart(3, "0")}`,
                doc_type: docType,
                customer_name: customerName,
                customer_email: customerEmail,
                customer_phone: customerPhone,
                customer_address: customerAddress || "Siège social client",
                issuer: issuer,
                items: [
                    {
                        product_name: itemName,
                        quantity: itemQty,
                        unit_price_ht: itemPrice,
                        tva_rate: itemTva,
                        total_ht: lineHt,
                        total_ttc: lineTtc
                    }
                ],
                total_ht: lineHt,
                tax_amount: lineTva,
                total_ttc: lineTtc,
                payment_terms: paymentTerms,
                status: "pending",
                language: lang,
                created_at: new Date().toISOString()
            };

            // Mise à jour du stock de produit si présent dans le catalogue
            if (window.NexaTenant) {
                const products = window.NexaTenant.getData("products", []);
                const prodIndex = products.findIndex(p => (p.name || "").toLowerCase() === itemName.toLowerCase());
                if (prodIndex !== -1 && products[prodIndex].stock !== undefined) {
                    products[prodIndex].stock = Math.max(0, (products[prodIndex].stock || 0) - itemQty);
                    window.NexaTenant.setData("products", products);
                }
            }

            list.unshift(newInv);
            saveTenantInvoices(list);
            modal.style.display = "none";
            fetchInvoices();
            alert(`✅ ${DOC_LABELS[normDocType(docType)]} N° ${newInv.number} créée avec succès dans votre espace entreprise !`);
            return;
        }

        // Mode API Serveur Réel
        const payload = {
            doc_type: docType,
            language: lang,
            issuer: {
                name: issuer.name,
                address: issuer.address,
                tax_id: issuer.tax_id || null,
                phone: issuer.phone,
                email: issuer.email,
                issuing_place: issuer.issuing_place
            },
            customer: {
                name: customerName,
                email: customerEmail || null,
                phone: customerPhone,
                address: customerAddress || "Siège social client"
            },
            items: [
                {
                    product_name: itemName,
                    quantity: itemQty,
                    unit_price_ht: itemPrice,
                    tva_rate: itemTva,
                    discount: 0.0,
                    unit: "U"
                }
            ],
            payment_terms: paymentTerms
        };

        if (submitBtn) submitBtn.disabled = true;
        try {
            const res = await fetch(`${API}/invoices/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            if (redirectIfUnauthorized(res)) return;

            if (!res.ok) {
                const errData = await res.json().catch(() => null);
                throw new Error(formatApiError(errData, `Erreur ${res.status} lors de la création de la facture`));
            }

            const created = await res.json();
            modal.style.display = "none";
            fetchInvoices();
            alert(`✅ Document N° ${created.number} créé avec succès !`);
        } catch (error) {
            console.warn("Échec d'envoi API, enregistrement dans l'espace isolé local :", error);
            // Repli automatique sur le stockage isolé
            const list = getTenantInvoices();
            const newId = list.length > 0 ? Math.max(...list.map(i => i.id || 0)) + 1 : 1;
            const newInv = {
                id: newId,
                number: `FAC-${new Date().toISOString().slice(0, 7).replace("-", "")}-${newId.toString().padStart(3, "0")}`,
                doc_type: docType,
                customer_name: customerName,
                customer_email: customerEmail,
                customer_phone: customerPhone,
                customer_address: customerAddress,
                issuer: issuer,
                items: [{ product_name: itemName, quantity: itemQty, unit_price_ht: itemPrice, tva_rate: itemTva }],
                total_ht: lineHt,
                tax_amount: lineTva,
                total_ttc: lineTtc,
                status: "pending",
                language: lang,
                created_at: new Date().toISOString()
            };
            list.unshift(newInv);
            saveTenantInvoices(list);
            modal.style.display = "none";
            fetchInvoices();
            alert(`✅ Document créé avec succès (sauvegardé dans l'espace isolé entreprise) !`);
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    });

    /* =========================================================================
       MODAL DE PAIEMENT
       ========================================================================= */

    function canPay(inv) {
        return normDocType(inv.doc_type) === "INVOICE" && inv.status === "pending";
    }

    const payModal      = document.getElementById("pay-modal");
    const payForm       = document.getElementById("pay-form");
    const payMethod     = document.getElementById("pay-method");
    const payManual     = document.getElementById("pay-manual-fields");
    const payOnlineInfo = document.getElementById("pay-online-info");
    const payError      = document.getElementById("pay-error");
    const paySubmit     = document.getElementById("pay-submit");
    let invoiceToPay    = null;

    function updatePayMode() {
        if (!payMethod) return;
        const online = payMethod.value === "online";
        if (payManual) payManual.style.display = online ? "none" : "block";
        if (payOnlineInfo) payOnlineInfo.style.display = online ? "block" : "none";
        if (paySubmit) {
            paySubmit.innerHTML = online
                ? '<i class="fa-solid fa-lock"></i> Payer en ligne'
                : '<i class="fa-solid fa-check"></i> Enregistrer le paiement';
        }
    }

    function openPayModal(invoiceId) {
        invoiceToPay = currentInvoices.find(i => String(i.id) === String(invoiceId));
        if (!invoiceToPay || !canPay(invoiceToPay)) return;

        document.getElementById("pay-invoice-number").textContent = invoiceToPay.number;
        document.getElementById("pay-customer").textContent = invoiceToPay.customer_name || "Client anonyme";
        document.getElementById("pay-amount").value = money(invoiceToPay.total_ttc);
        document.getElementById("pay-date").value = new Date().toISOString().slice(0, 10);
        document.getElementById("pay-reference").value = "";
        if (payMethod) payMethod.value = "cash";
        if (payError) payError.style.display = "none";
        updatePayMode();
        if (payModal) payModal.style.display = "block";
    }

    function closePayModal() {
        if (payModal) payModal.style.display = "none";
        invoiceToPay = null;
    }

    if (payMethod) payMethod.addEventListener("change", updatePayMode);
    document.getElementById("pay-close")?.addEventListener("click", closePayModal);
    window.addEventListener("click", (e) => { if (e.target === payModal) closePayModal(); });

    if (payForm) {
        payForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (!invoiceToPay) return;

            if (isDemo || !window.API) {
                // Règle la facture dans le registre isolé local
                const list = getTenantInvoices();
                const idx = list.findIndex(i => String(i.id) === String(invoiceToPay.id));
                if (idx !== -1) {
                    list[idx].status = "paid";
                    list[idx].paid_at = document.getElementById("pay-date").value;
                    saveTenantInvoices(list);
                }
                closePayModal();
                fetchInvoices();
                alert("✅ Paiement enregistré avec succès ! La facture est désormais marquée comme PAYÉE.");
                return;
            }

            if (payError) payError.style.display = "none";
            if (paySubmit) paySubmit.disabled = true;
            const headers = { "Content-Type": "application/json", "Authorization": `Bearer ${token}` };

            try {
                let res;
                if (payMethod.value === "online") {
                    res = await fetch(`${API}/invoices/${invoiceToPay.id}/online-payment`, {
                        method: "POST",
                        headers,
                        body: JSON.stringify({
                            success_url: `${location.origin}${location.pathname}?payment=success`,
                            cancel_url:  `${location.origin}${location.pathname}?payment=cancel`
                        })
                    });
                } else {
                    res = await fetch(`${API}/invoices/${invoiceToPay.id}/payments`, {
                        method: "POST",
                        headers,
                        body: JSON.stringify({
                            method: payMethod.value,
                            amount: Number(invoiceToPay.total_ttc),
                            paid_at: document.getElementById("pay-date").value,
                            reference: document.getElementById("pay-reference").value.trim() || null
                        })
                    });
                }

                if (redirectIfUnauthorized(res)) return;

                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(formatApiError(data, "Le paiement a échoué."));
                }

                if (payMethod.value === "online") {
                    if (!data.payment_url) throw new Error("Lien de paiement indisponible.");
                    window.location.href = data.payment_url;
                    return;
                }

                closePayModal();
                await fetchInvoices();
                alert(tr("payment_saved"));
            } catch (err) {
                if (payError) {
                    payError.textContent = err.message;
                    payError.style.display = "block";
                }
            } finally {
                if (paySubmit) paySubmit.disabled = false;
            }
        });
    }

    // Pré-remplir le client si envoyé depuis la page Clients
    const prefillCustomer = localStorage.getItem("prefill_invoice_customer");
    if (prefillCustomer && modal) {
        localStorage.removeItem("prefill_invoice_customer");
        if (invoiceForm) invoiceForm.reset();
        fillIssuerForm();
        populateDatalists();
        const custInput = document.getElementById("customer-name");
        if (custInput) custInput.value = prefillCustomer;
        modal.style.display = "block";
    }

    populateDatalists();
    fetchInvoices();
});
