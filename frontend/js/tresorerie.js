const API = window.API || "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
    const token = sessionStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    let state = { accounts: [], movements: [], open_invoices: [], open_purchases: [] };
    let direction = "in";
    const METHODS = { cash: "Espèces", bank_transfer: "Virement", cheque: "Chèque", mobile_money: "Mobile money" };

    const companyContext = document.getElementById("company-context");
    if (companyContext && window.NexaTenant) {
        const sessionUser = window.NexaTenant.getCurrentUser();
        const companyName = sessionUser.company_name || sessionUser.tenant_id || "votre entreprise";
        companyContext.textContent = `Entreprise connectée : ${companyName}. La caisse et la banque de cet espace sont séparées des autres entreprises.`;
    }

    function headers(json) {
        const value = { Authorization: `Bearer ${token}` };
        if (json) value["Content-Type"] = "application/json";
        return value;
    }
    function money(value) {
        return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(value || 0) + " F";
    }
    function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }
    function apiError(data, fallback) {
        return data && typeof data.detail === "string" ? data.detail : fallback;
    }

    function showTab(name) {
        ["mouvements", "factures", "achats"].forEach((tab) => {
            document.getElementById(`panel-${tab}`).hidden = tab !== name;
        });
        document.querySelectorAll(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === name));
    }
    document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", () => showTab(button.dataset.tab)));

    function render() {
        document.getElementById("kpi-balance").textContent = money(state.balance);
        document.getElementById("kpi-in").textContent = money(state.cash_in);
        document.getElementById("kpi-out").textContent = money(state.cash_out);
        document.getElementById("kpi-due").textContent = money(state.receivable);
        document.getElementById("account-line").textContent = (state.accounts || [])
            .map((account) => `${account.name} : ${money(account.balance)}`)
            .join("  ·  ");
        const select = document.getElementById("move-account");
        select.innerHTML = (state.accounts || []).map((account) => `<option value="${account.id}">${escapeHtml(account.name)}</option>`).join("");
        const movements = state.movements || [];
        document.getElementById("movements-body").innerHTML = movements.length ? movements.map((item) => `
            <tr>
                <td>${escapeHtml(item.movement_date)}</td>
                <td>${escapeHtml(item.account_name)}</td>
                <td>${escapeHtml(item.label)}</td>
                <td>${escapeHtml(item.party_name || "—")}</td>
                <td><span class="pill ${item.direction === "in" ? "in" : "out"}">${item.direction === "in" ? "Entrée" : "Sortie"}</span></td>
                <td>${money(item.amount)}<br><small>${METHODS[item.method] || item.method}</small></td>
            </tr>
        `).join("") : `<tr><td colspan="6" style="text-align:center;padding:24px;">Aucun mouvement pour cette entreprise.</td></tr>`;
        const invoices = state.open_invoices || [];
        document.getElementById("invoices-body").innerHTML = invoices.length ? invoices.map((item) => `
            <tr>
                <td>${escapeHtml(item.number)}</td>
                <td>${escapeHtml(item.party_name)}</td>
                <td>${money(item.total_ttc)}</td>
                <td>${money(item.paid)}</td>
                <td>${money(item.remaining)}</td>
                <td><button class="btn-action-small" data-collect="${item.id}" data-amount="${item.remaining}">Encaisser</button></td>
            </tr>
        `).join("") : `<tr><td colspan="6" style="text-align:center;padding:24px;">Aucune facture à encaisser.</td></tr>`;
        const purchases = state.open_purchases || [];
        document.getElementById("purchases-body").innerHTML = purchases.length ? purchases.map((item) => `
            <tr>
                <td>${escapeHtml(item.number)}</td>
                <td>${escapeHtml(item.party_name || "—")}</td>
                <td>${money(item.total_ttc)}</td>
                <td>${money(item.paid)}</td>
                <td>${money(item.remaining)}</td>
                <td><button class="btn-action-small" data-pay="${item.id}" data-amount="${item.remaining}">Payer</button></td>
            </tr>
        `).join("") : `<tr><td colspan="6" style="text-align:center;padding:24px;">Aucun achat confirmé à payer.</td></tr>`;
    }

    async function load() {
        const res = await fetch(`${API}/treasury/overview`, { headers: headers() });
        if (res.status === 401) {
            window.location.href = "index.html";
            return;
        }
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            document.getElementById("movements-body").innerHTML = `<tr><td colspan="6" style="color:#991b1b;padding:24px;">${escapeHtml(apiError(data, "Impossible de charger la trésorerie."))}</td></tr>`;
            return;
        }
        state = data;
        render();
    }

    function openMove(nextDirection) {
        direction = nextDirection;
        document.getElementById("move-title").textContent = nextDirection === "in" ? "Encaissement" : "Décaissement";
        document.getElementById("move-form").reset();
        document.getElementById("move-label").value = nextDirection === "in" ? "Encaissement divers" : "Dépense";
        document.getElementById("move-modal").style.display = "block";
    }
    document.getElementById("open-in").addEventListener("click", () => openMove("in"));
    document.getElementById("open-out").addEventListener("click", () => openMove("out"));
    document.querySelectorAll("[data-close]").forEach((button) => {
        button.addEventListener("click", () => { document.getElementById(button.dataset.close).style.display = "none"; });
    });

    document.getElementById("move-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const res = await fetch(`${API}/treasury/movements`, {
            method: "POST",
            headers: headers(true),
            body: JSON.stringify({
                account_id: Number(document.getElementById("move-account").value),
                direction,
                amount: Number(document.getElementById("move-amount").value),
                method: document.getElementById("move-method").value,
                label: document.getElementById("move-label").value.trim(),
                party_name: document.getElementById("move-party").value.trim(),
                reference: document.getElementById("move-reference").value.trim(),
            }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            alert(apiError(data, "Mouvement refusé."));
            return;
        }
        document.getElementById("move-modal").style.display = "none";
        state = data;
        render();
        showTab("mouvements");
    });

    document.getElementById("invoices-body").addEventListener("click", async (event) => {
        const button = event.target.closest("[data-collect]");
        if (!button) return;
        const res = await fetch(`${API}/invoices/${button.dataset.collect}/payments`, {
            method: "POST",
            headers: headers(true),
            body: JSON.stringify({ method: "cash", amount: Number(button.dataset.amount) }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            alert(apiError(data, "Encaissement refusé."));
            return;
        }
        await load();
        showTab("factures");
    });

    document.getElementById("purchases-body").addEventListener("click", async (event) => {
        const button = event.target.closest("[data-pay]");
        if (!button) return;
        const res = await fetch(`${API}/treasury/purchases/${button.dataset.pay}/pay`, {
            method: "POST",
            headers: headers(true),
            body: JSON.stringify({ method: "bank_transfer", amount: Number(button.dataset.amount) }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            alert(apiError(data, "Paiement refusé."));
            return;
        }
        state = data;
        render();
        showTab("achats");
    });

    load();
});
