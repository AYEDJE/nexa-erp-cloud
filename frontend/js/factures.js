const API = 'http://127.0.0.1:8000';

document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    const tableBody = document.getElementById("invoices-table-body");
    const modal = document.getElementById("invoice-modal");
    const openModalBtn = document.getElementById("open-invoice-modal");
    const closeModalBtn = document.getElementById("close-modal");
    const invoiceForm = document.getElementById("invoice-form");

    const kpiTotalTtc = document.getElementById("kpi-total-ttc");
    const kpiCountPayees = document.getElementById("kpi-count-payees");
    const kpiCountAttente = document.getElementById("kpi-count-attente");

    const isDemo = token.startsWith("demo_");

    function getDemoInvoices() {
        const stored = localStorage.getItem("demo_invoices");
        if (stored) return JSON.parse(stored);
        const defaults = [
            {
                id: 1,
                number: "FAC-202610-001",
                doc_type: "FACTURE",
                customer_name: "Société Commerciale Alpha",
                customer_email: "direction@alpha.com",
                total_ht: 1500.0,
                tax_amount: 285.0,
                total_ttc: 1785.0,
                status: "paid",
                language: "fr"
            },
            {
                id: 2,
                number: "FAC-202610-002",
                doc_type: "FACTURE",
                customer_name: "Cabinet Conseil Pro",
                customer_email: "contact@conseilpro.fr",
                total_ht: 850.0,
                tax_amount: 161.5,
                total_ttc: 1011.5,
                status: "pending",
                language: "fr"
            },
            {
                id: 3,
                number: "DEV-202610-003",
                doc_type: "DEVIS",
                customer_name: "Groupe Industriel Moderne",
                customer_email: "achats@gim-group.com",
                total_ht: 3200.0,
                tax_amount: 608.0,
                total_ttc: 3808.0,
                status: "draft",
                language: "fr"
            }
        ];
        localStorage.setItem("demo_invoices", JSON.stringify(defaults));
        return defaults;
    }

    // Récupération des factures
    async function fetchInvoices() {
        if (isDemo) {
            const list = getDemoInvoices();
            renderTable(list);
            updateKPIs(list);
            return;
        }

        try {
            const response = await fetch(`${API}/invoices/`, {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            if (response.status === 401) {
                localStorage.removeItem("access_token");
                window.location.href = "index.html";
                return;
            }

            if (!response.ok) throw new Error("Erreur de récupération des factures");
            const invoices = await response.json();
            renderTable(invoices);
            updateKPIs(invoices);
        } catch (error) {
            console.warn("Échec serveur, passage temporaire en données démo locale :", error);
            const demoList = getDemoInvoices();
            renderTable(demoList);
            updateKPIs(demoList);
        }
    }

    function updateKPIs(list) {
        if (!list) return;
        const total = list.reduce((sum, inv) => sum + (parseFloat(inv.total_ttc) || 0), 0);
        const payees = list.filter(inv => inv.status === "paid").length;
        const attente = list.filter(inv => inv.status === "pending" || inv.status === "draft").length;

        if (kpiTotalTtc) kpiTotalTtc.textContent = `${total.toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;
        if (kpiCountPayees) kpiCountPayees.textContent = payees;
        if (kpiCountAttente) kpiCountAttente.textContent = attente;
    }

    // Affichage dans le tableau HTML
    function renderTable(invoices) {
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

            const docBadge = inv.doc_type === "DEVIS" ? "background:#f3e8ff; color:#7e22ce;" : "background:#e0f2fe; color:#0369a1;";

            return `
            <tr>
                <td><strong>${inv.number}</strong></td>
                <td><span style="padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; ${docBadge}">${inv.doc_type || 'FACTURE'}</span></td>
                <td>${inv.customer_name || 'Client anonyme'}</td>
                <td>${Number(inv.total_ht || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €</td>
                <td><strong style="color:#111827;">${Number(inv.total_ttc || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €</strong></td>
                <td><span class="status-pill ${statusClass}">${statusLabel}</span></td>
                <td style="text-align: center;">
                    <button class="btn-action pdf" data-id="${inv.id}" data-number="${inv.number}" title="Télécharger le PDF officiel">
                        <i class="fa-solid fa-file-pdf"></i> PDF
                    </button>
                </td>
            </tr>
            `;
        }).join("");

        // Écouteurs pour le téléchargement PDF
        document.querySelectorAll(".btn-action.pdf").forEach(btn => {
            btn.addEventListener("click", () => handleDownloadPDF(btn.dataset.id, btn.dataset.number));
        });
    }

    // Télécharger le PDF officiel de la facture
    async function handleDownloadPDF(invoiceId, invoiceNumber) {
        if (isDemo) {
            alert(`[MODE DÉMO] Simulation du téléchargement de la facture PDF "${invoiceNumber}". Connectez-vous au backend réel pour obtenir le PDF généré avec ReportLab et le montant en toutes lettres.`);
            return;
        }

        try {
            const btn = document.querySelector(`.btn-action.pdf[data-id="${invoiceId}"]`);
            if (btn) btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Génération...`;

            const res = await fetch(`${API}/invoices/${invoiceId}/pdf?lang=fr`, {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            if (!res.ok) throw new Error("Erreur lors de la génération du PDF.");

            const blob = await res.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = downloadUrl;
            a.download = `Facture_${invoiceNumber || invoiceId}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(downloadUrl);

            if (btn) btn.innerHTML = `<i class="fa-solid fa-file-pdf"></i> PDF`;
        } catch (err) {
            console.error(err);
            alert("Erreur de téléchargement : " + err.message);
        }
    }

    // Gestion de la modale
    if (openModalBtn) {
        openModalBtn.addEventListener("click", () => {
            invoiceForm.reset();
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

    // Envoi du formulaire de création
    invoiceForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const docType = document.getElementById("doc-type").value;
        const lang = document.getElementById("inv-lang").value;
        const customerName = document.getElementById("customer-name").value.trim();
        const customerEmail = document.getElementById("customer-email").value.trim();
        const itemName = document.getElementById("item-name").value.trim();
        const itemQty = parseFloat(document.getElementById("item-qty").value) || 1;
        const itemPrice = parseFloat(document.getElementById("item-price").value) || 0;
        const itemTva = parseFloat(document.getElementById("item-tva").value) || 19.0;
        const paymentTerms = document.getElementById("payment-terms").value.trim();

        const lineHt = itemQty * itemPrice;
        const lineTva = lineHt * (itemTva / 100.0);
        const lineTtc = lineHt + lineTva;

        if (isDemo) {
            const demoList = getDemoInvoices();
            const newId = demoList.length > 0 ? Math.max(...demoList.map(i => i.id)) + 1 : 1;
            const newInv = {
                id: newId,
                number: `${docType.substring(0,3)}-202610-00${newId}`,
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
            alert(`Facture ${newInv.number} créée avec succès !`);
            return;
        }

        // Appel API Backend réel
        const payload = {
            doc_type: docType,
            language: lang,
            issuer: {
                name: "Nexa ERP Cloud",
                address: "123 Avenue Habib Bourguiba, Tunis",
                tax_id: "MF-1234567-NEXA"
            },
            customer: {
                name: customerName,
                email: customerEmail,
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

        try {
            const res = await fetch(`${API}/invoices/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Erreur de création de la facture");
            }

            const created = await res.json();
            modal.style.display = "none";
            fetchInvoices();
            alert(`Facture ${created.number} générée avec succès !`);
        } catch (error) {
            console.error(error);
            alert("Erreur : " + error.message);
        }
    });

    fetchInvoices();

    // Pré-remplir le client si envoyé depuis la page Clients
    const prefillCustomer = localStorage.getItem("prefill_invoice_customer");
    if (prefillCustomer && modal) {
        localStorage.removeItem("prefill_invoice_customer");
        if (invoiceForm) invoiceForm.reset();
        const custInput = document.getElementById("customer-name");
        if (custInput) custInput.value = prefillCustomer;
        modal.style.display = "block";
    }
});
