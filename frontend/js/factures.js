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

    const isDemo = token.startsWith("demo_");
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

    const COMPANY_KEY = "company_profile";
    const ISSUER_FIELDS = {
        name: "issuer-name",
        tax_id: "issuer-tax-id",
        address: "issuer-address",
        phone: "issuer-phone",
        email: "issuer-email",
        issuing_place: "issuer-place"
    };

    function loadCompanyProfile() {
        try { return JSON.parse(localStorage.getItem(COMPANY_KEY)) || {}; } catch (_) { return {}; }
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
        
    async function syncCompanyProfile() {
        if (isDemo) return;
        try {
            const res = await fetch(`${API}/company/`, { headers: { "Authorization": `Bearer ${token}` } });
            if (res.ok) {
                const c = await res.json();
                const clean = Object.fromEntries(Object.entries(c).filter(([, v]) => v !== null && v !== ""));
                localStorage.setItem(COMPANY_KEY, JSON.stringify(clean));
            }
        } catch (_) { /* on garde la copie locale */ }
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


    function getDemoInvoices() {
        const stored = localStorage.getItem("demo_invoices");
        if (stored) return JSON.parse(stored);
        const defaults = [
            { id: 1, number: "FAC-202610-001", doc_type: "INVOICE", customer_name: "Société Commerciale Alpha", customer_email: "direction@alpha.com", total_ht: 1500.0, tax_amount: 285.0, total_ttc: 1785.0, status: "paid", language: "fr" },
            { id: 2, number: "FAC-202610-002", doc_type: "INVOICE", customer_name: "Cabinet Conseil Pro", customer_email: "contact@conseilpro.fr", total_ht: 850.0, tax_amount: 161.5, total_ttc: 1011.5, status: "pending", language: "fr" },
            { id: 3, number: "DEV-202610-003", doc_type: "QUOTE", customer_name: "Groupe Industriel Moderne", customer_email: "achats@gim-group.com", total_ht: 3200.0, tax_amount: 608.0, total_ttc: 3808.0, status: "draft", language: "fr" }
        ];
        localStorage.setItem("demo_invoices", JSON.stringify(defaults));
        return defaults;
    }

    
    async function fetchInvoices() {
        if (isDemo) {
            const list = getDemoInvoices();
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
            console.error("Impossible de charger les factures :", error);
            // Plus de fausses données : on montre l'erreur réelle
            currentInvoices = [];
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 24px; color:#dc2626;">${escapeHtml(error.message)}</td></tr>`;
            updateKPIs([]);
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
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 24px; color: #6b7280;">Aucune facture trouvée. Cliquez sur "Nouvelle Facture" pour en créer une.</td></tr>`;
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
                <td>${escapeHtml(inv.customer_name) || "Client anonyme"}</td>
                <td>${money(inv.total_ht)}</td>
                <td><strong style="color:#111827;">${money(inv.total_ttc)}</strong></td>
                <td><span class="status-pill ${statusClass}">${statusLabel}</span></td>
                <td style="text-align: center;">
                    ${canPay(inv) ? `<button class="btn-action pay" data-id="${inv.id}" title="Régler cette facture" style="margin-right:4px; color:#166534; border-color:#bbf7d0;">
                        <i class="fa-solid fa-money-bill-wave"></i> Régler
                    </button>` : ""}
                    <button class="btn-action pdf" data-id="${inv.id}" data-number="${escapeHtml(inv.number)}" title="Télécharger le PDF officiel">
                        <i class="fa-solid fa-file-pdf"></i> PDF
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
    }

    async function handleDownloadPDF(invoiceId, invoiceNumber) {
        if (isDemo) {
            alert(`[MODE DÉMO] Simulation du téléchargement de la facture PDF "${invoiceNumber}".`);
            return;
        }

        const btn = document.querySelector(`.btn-action.pdf[data-id="${invoiceId}"]`);
        const originalHtml = btn ? btn.innerHTML : "";
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Génération...`;
        }

        try {
            const inv = currentInvoices.find(i => String(i.id) === String(invoiceId));
            const lang = (inv && inv.language) || (window.i18n && window.i18n.getLang()) || "fr";

            const res = await fetch(`${API}/invoices/${invoiceId}/pdf?lang=${encodeURIComponent(lang)}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (redirectIfUnauthorized(res)) return;

            if (!res.ok) {
                const errData = await res.json().catch(() => null);
                console.error("Réponse API (PDF) :", res.status, errData);
                throw new Error(formatApiError(errData, `Erreur ${res.status} lors de la génération du PDF.`));
            }

            const blob = await res.blob();
            if (blob.type && !blob.type.includes("pdf") && !blob.type.includes("octet-stream")) {
                throw new Error("Le serveur n'a pas renvoyé un PDF valide.");
            }

            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = downloadUrl;
            a.download = `Facture_${invoiceNumber || invoiceId}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(downloadUrl);
        } catch (err) {
            console.error(err);
            alert(tr("error_prefix", { msg: err.message }));
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        }
    }

    if (openModalBtn) {
        openModalBtn.addEventListener("click", () => {
            invoiceForm.reset();
            fillIssuerForm();
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
        const issuer = readIssuerForm();
        const itemName = document.getElementById("item-name").value.trim();
        const itemQty = parseFloat(document.getElementById("item-qty").value) || 1;
        const itemPrice = parseFloat(document.getElementById("item-price").value) || 0;
        const rawTva = parseFloat(document.getElementById("item-tva").value);
        const itemTva = Number.isNaN(rawTva) ? 19.0 : rawTva;   // 0 % reste possible
        const paymentTerms = document.getElementById("payment-terms").value.trim();

        const lineHt = itemQty * itemPrice;
        const lineTva = lineHt * (itemTva / 100.0);
        const lineTtc = lineHt + lineTva;

        if (isDemo) {
            const demoList = getDemoInvoices();
            const newId = demoList.length > 0 ? Math.max(...demoList.map(i => i.id)) + 1 : 1;
            const newInv = {
                id: newId,
                number: `${docType.substring(0, 3)}-202610-00${newId}`,
                doc_type: docType,
                customer_name: customerName,
                customer_email: customerEmail,
                total_ht: lineHt,
                tax_amount: lineTva,
                total_ttc: lineTtc,
                status: "pending",
                language: lang
            };
            demoList.unshift(newInv);
            localStorage.setItem("demo_invoices", JSON.stringify(demoList));
            modal.style.display = "none";
            fetchInvoices();
            alert(tr("invoice_created", { number: newInv.number }));
            return;
        }

        // On mémorise l'émetteur pour les prochaines factures
        localStorage.setItem(COMPANY_KEY, JSON.stringify({ ...loadCompanyProfile(), ...issuer }));

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
                address: "Siège social client"
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
                console.error("Réponse API (création facture) :", res.status, errData, "Payload envoyé :", payload);
                throw new Error(formatApiError(errData, `Erreur ${res.status} de création de la facture`));
            }

            const created = await res.json();
            modal.style.display = "none";
            fetchInvoices();
            alert(tr("invoice_created", { number: created.number }));
        } catch (error) {
            console.error(error);
            alert(tr("error_prefix", { msg: error.message }));
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    });

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
        const online = payMethod.value === "online";
        payManual.style.display = online ? "none" : "block";
        payOnlineInfo.style.display = online ? "block" : "none";
        paySubmit.innerHTML = online
            ? '<i class="fa-solid fa-lock"></i> Payer en ligne'
            : '<i class="fa-solid fa-check"></i> Enregistrer le paiement';
    }

    function openPayModal(invoiceId) {
        invoiceToPay = currentInvoices.find(i => String(i.id) === String(invoiceId));
        if (!invoiceToPay || !canPay(invoiceToPay)) return;

        document.getElementById("pay-invoice-number").textContent = invoiceToPay.number;
        document.getElementById("pay-customer").textContent = invoiceToPay.customer_name || "Client anonyme";
        document.getElementById("pay-amount").value = money(invoiceToPay.total_ttc);
        document.getElementById("pay-date").value = new Date().toISOString().slice(0, 10);
        document.getElementById("pay-reference").value = "";
        payMethod.value = "cash";
        payError.style.display = "none";
        updatePayMode();
        payModal.style.display = "block";
    }

    function closePayModal() {
        payModal.style.display = "none";
        invoiceToPay = null;
    }

    payMethod.addEventListener("change", updatePayMode);
    document.getElementById("pay-close").addEventListener("click", closePayModal);
    window.addEventListener("click", (e) => { if (e.target === payModal) closePayModal(); });

    payForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!invoiceToPay) return;

        payError.style.display = "none";
        paySubmit.disabled = true;
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
                console.error("Réponse API (paiement) :", res.status, data);
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
            payError.textContent = err.message;
            payError.style.display = "block";
        } finally {
            paySubmit.disabled = false;
        }
    });

    // Retour depuis la page de paiement en ligne
    const payResult = new URLSearchParams(location.search).get("payment");
    if (payResult) {
        history.replaceState(null, "", location.pathname);
        if (payResult === "success") alert(tr("payment_success"));
        else if (payResult === "cancel") alert(tr("payment_cancel"));
    }

    // Les montants du tableau suivent la langue choisie
    document.addEventListener("langchange", () => {
        if (currentInvoices.length) {
            renderTable(currentInvoices);
            updateKPIs(currentInvoices);
        }
    });

    fetchInvoices();

    // Pré-remplir le client si envoyé depuis la page Clients
    const prefillCustomer = localStorage.getItem("prefill_invoice_customer");
    if (prefillCustomer && modal) {
        localStorage.removeItem("prefill_invoice_customer");
        if (invoiceForm) invoiceForm.reset();
        fillIssuerForm();
        const custInput = document.getElementById("customer-name");
        if (custInput) custInput.value = prefillCustomer;
        modal.style.display = "block";
    }
});