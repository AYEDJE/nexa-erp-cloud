const API = window.API || "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
    const token = sessionStorage.getItem("access_token") || localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    const STATUS = {
        draft: ["Brouillon", "#fef3c7", "#b45309"],
        confirmed: ["Commandée", "#e0f2fe", "#0369a1"],
        partial: ["Réception partielle", "#ede9fe", "#6d28d9"],
        received: ["Réceptionnée", "#dcfce7", "#166534"],
        cancelled: ["Annulée", "#f3f4f6", "#6b7280"],
    };

    let suppliers = [];
    let orders = [];
    let products = [];

    const ordersBody = document.getElementById("orders-body");
    const suppliersBody = document.getElementById("suppliers-body");
    const companyContext = document.getElementById("company-context");
    if (companyContext && window.NexaTenant) {
        const sessionUser = window.NexaTenant.getCurrentUser();
        const companyName = sessionUser.company_name || sessionUser.tenant_id || "votre entreprise";
        companyContext.textContent = `Entreprise connectée : ${companyName}. Les fournisseurs et les bons de commande restent dans cet espace.`;
    }

    function authHeaders(json) {
        const headers = { Authorization: `Bearer ${token}` };
        if (json) headers["Content-Type"] = "application/json";
        return headers;
    }

    function apiError(data, fallback) {
        const detail = data && data.detail;
        if (typeof detail === "string") return detail;
        return fallback;
    }

    function money(value) {
        return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(value || 0) + " F";
    }

    function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, (char) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        }[char]));
    }

    function showTab(name) {
        const suppliersTab = name === "fournisseurs";
        document.getElementById("panel-commandes").hidden = suppliersTab;
        document.getElementById("panel-fournisseurs").hidden = !suppliersTab;
        document.querySelectorAll(".tab").forEach((button) => {
            button.classList.toggle("active", button.dataset.tab === name);
        });
        document.getElementById("page-title").textContent = suppliersTab ? "Fournisseurs" : "Achats";
        document.getElementById("nav-achats").classList.toggle("active", !suppliersTab);
        document.getElementById("nav-fournisseurs").classList.toggle("active", suppliersTab);
    }

    document.querySelectorAll(".tab").forEach((button) => {
        button.addEventListener("click", () => {
            const name = button.dataset.tab;
            showTab(name);
            history.replaceState(null, "", name === "fournisseurs" ? "#fournisseurs" : "achats.html");
        });
    });
    showTab(location.hash === "#fournisseurs" ? "fournisseurs" : "commandes");

    function openModal(id) {
        document.getElementById(id).style.display = "block";
    }
    function closeModal(id) {
        document.getElementById(id).style.display = "none";
    }
    document.querySelectorAll("[data-close]").forEach((button) => {
        button.addEventListener("click", () => closeModal(button.dataset.close));
    });
    window.addEventListener("click", (event) => {
        if (event.target.classList.contains("modal")) event.target.style.display = "none";
    });

    function renderSuppliers() {
        const active = suppliers.filter((supplier) => supplier.is_active);
        document.getElementById("kpi-suppliers").textContent = String(active.length);
        const select = document.getElementById("order-supplier");
        select.innerHTML = active.map((supplier) => `<option value="${supplier.id}">${escapeHtml(supplier.name)}</option>`).join("");
        if (!active.length) select.innerHTML = `<option value="">Aucun fournisseur actif</option>`;
        suppliersBody.innerHTML = suppliers.length ? suppliers.map((supplier) => `
            <tr>
                <td>${escapeHtml(supplier.name)}</td>
                <td>${escapeHtml(supplier.contact_name || "—")}</td>
                <td>${escapeHtml(supplier.email || "—")}</td>
                <td>${escapeHtml(supplier.phone || "—")}</td>
                <td>${escapeHtml(supplier.tax_id || "—")}</td>
                <td>${supplier.is_active ? "Actif" : "Inactif"}</td>
            </tr>
        `).join("") : `<tr><td colspan="6" style="text-align:center; padding:24px;">Aucun fournisseur pour cette entreprise.</td></tr>`;
    }

    function renderOrders() {
        const open = orders.filter((order) => order.status === "draft" || order.status === "confirmed" || order.status === "partial");
        const incoming = orders.filter((order) => order.status === "confirmed" || order.status === "partial");
        const amount = orders.filter((order) => order.status !== "cancelled").reduce((sum, order) => sum + Number(order.total_ttc || 0), 0);
        document.getElementById("kpi-open").textContent = String(open.length);
        document.getElementById("kpi-incoming").textContent = String(incoming.length);
        document.getElementById("kpi-amount").textContent = money(amount);
        ordersBody.innerHTML = orders.length ? orders.map((order) => {
            const style = STATUS[order.status] || STATUS.draft;
            const lines = order.lines.map((line) => `${escapeHtml(line.product_name)} (${line.received_qty}/${line.quantity})`).join("<br>");
            const actions = [];
            if (order.status === "draft") {
                actions.push(`<button class="btn-action-small" data-action="confirm" data-id="${order.id}">Commander</button>`);
                actions.push(`<button class="btn-action-small" data-action="cancel" data-id="${order.id}">Annuler</button>`);
            }
            if (order.status === "confirmed" || order.status === "partial") {
                actions.push(`<button class="btn-action-small" data-action="receive" data-id="${order.id}">Réceptionner</button>`);
                if (order.lines.every((line) => Number(line.received_qty) === 0)) {
                    actions.push(`<button class="btn-action-small" data-action="cancel" data-id="${order.id}">Annuler</button>`);
                }
            }
            return `
                <tr>
                    <td>${escapeHtml(order.number)}</td>
                    <td>${escapeHtml(order.supplier_name)}</td>
                    <td><span class="status-pill" style="background:${style[1]};color:${style[2]}">${style[0]}</span></td>
                    <td>${money(order.total_ttc)}</td>
                    <td>${lines}</td>
                    <td style="display:flex; gap:6px; flex-wrap:wrap;">${actions.join("")}</td>
                </tr>`;
        }).join("") : `<tr><td colspan="6" style="text-align:center; padding:24px;">Aucun bon de commande. Créez un fournisseur, puis une commande.</td></tr>`;
    }

    async function loadAll() {
        const [supplierRes, orderRes, productRes] = await Promise.all([
            fetch(`${API}/purchases/suppliers`, { headers: authHeaders() }),
            fetch(`${API}/purchases/orders`, { headers: authHeaders() }),
            fetch(`${API}/products/`, { headers: authHeaders() }),
        ]);
        if ([supplierRes, orderRes].some((res) => res.status === 401)) {
            window.location.href = "index.html";
            return;
        }
        if (!supplierRes.ok || !orderRes.ok) {
            const data = await (supplierRes.ok ? orderRes : supplierRes).json().catch(() => ({}));
            ordersBody.innerHTML = `<tr><td colspan="6" style="color:#991b1b; padding:24px;">${escapeHtml(apiError(data, "Impossible de charger les achats."))}</td></tr>`;
            return;
        }
        suppliers = await supplierRes.json();
        orders = await orderRes.json();
        products = productRes.ok ? await productRes.json() : [];
        renderSuppliers();
        renderOrders();
    }

    function lineTemplate() {
        const options = [`<option value="">Saisie libre</option>`].concat(
            products.map((product) => `<option value="${product.id}">${escapeHtml(product.name)}</option>`)
        ).join("");
        const row = document.createElement("div");
        row.className = "line-row";
        row.innerHTML = `
            <select class="line-product">${options}</select>
            <input class="line-name" placeholder="Article" required>
            <input class="line-qty" type="number" min="0.01" step="0.01" value="1" required>
            <input class="line-price" type="number" min="0" step="0.01" value="0" required>
            <button type="button" class="btn-action-small line-remove">×</button>
        `;
        const select = row.querySelector(".line-product");
        const name = row.querySelector(".line-name");
        select.addEventListener("change", () => {
            const product = products.find((item) => String(item.id) === select.value);
            if (product) {
                name.value = product.name;
                row.querySelector(".line-price").value = product.price;
            }
        });
        row.querySelector(".line-remove").addEventListener("click", () => {
            if (document.querySelectorAll(".line-row").length > 1) row.remove();
        });
        return row;
    }

    document.getElementById("add-line").addEventListener("click", () => {
        document.getElementById("order-lines").appendChild(lineTemplate());
    });

    document.getElementById("open-supplier-modal").addEventListener("click", () => {
        document.getElementById("supplier-form").reset();
        openModal("supplier-modal");
    });
    document.getElementById("open-order-modal").addEventListener("click", () => {
        document.getElementById("order-form").reset();
        const holder = document.getElementById("order-lines");
        holder.innerHTML = "";
        holder.appendChild(lineTemplate());
        openModal("order-modal");
    });

    document.getElementById("supplier-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = {
            name: document.getElementById("supplier-name").value.trim(),
            contact_name: document.getElementById("supplier-contact").value.trim(),
            phone: document.getElementById("supplier-phone").value.trim(),
            email: document.getElementById("supplier-email").value.trim(),
            tax_id: document.getElementById("supplier-tax").value.trim(),
            address: document.getElementById("supplier-address").value.trim(),
        };
        const res = await fetch(`${API}/purchases/suppliers`, {
            method: "POST",
            headers: authHeaders(true),
            body: JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            alert(apiError(data, "Impossible d'enregistrer ce fournisseur."));
            return;
        }
        closeModal("supplier-modal");
        await loadAll();
        showTab("fournisseurs");
    });

    document.getElementById("order-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const supplierId = Number(document.getElementById("order-supplier").value);
        if (!supplierId) {
            alert("Enregistrez d'abord un fournisseur.");
            return;
        }
        const lines = [...document.querySelectorAll(".line-row")].map((row) => ({
            product_id: row.querySelector(".line-product").value ? Number(row.querySelector(".line-product").value) : null,
            product_name: row.querySelector(".line-name").value.trim(),
            quantity: Number(row.querySelector(".line-qty").value),
            unit_price_ht: Number(row.querySelector(".line-price").value),
            tva_rate: 18,
        }));
        const res = await fetch(`${API}/purchases/orders`, {
            method: "POST",
            headers: authHeaders(true),
            body: JSON.stringify({
                supplier_id: supplierId,
                notes: document.getElementById("order-notes").value.trim(),
                lines,
            }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            alert(apiError(data, "Impossible d'enregistrer la commande."));
            return;
        }
        closeModal("order-modal");
        await loadAll();
        showTab("commandes");
    });

    ordersBody.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-action]");
        if (!button) return;
        const order = orders.find((item) => String(item.id) === button.dataset.id);
        if (!order) return;
        if (button.dataset.action === "receive") {
            openReceive(order);
            return;
        }
        if (button.dataset.action === "cancel" && !confirm(`Annuler ${order.number} ?`)) return;
        const res = await fetch(`${API}/purchases/orders/${order.id}/${button.dataset.action}`, {
            method: "POST",
            headers: authHeaders(),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            alert(apiError(data, "Action impossible."));
            return;
        }
        await loadAll();
    });

    function openReceive(order) {
        document.getElementById("receive-title").textContent = `Réception ${order.number}`;
        const form = document.getElementById("receive-form");
        form.innerHTML = order.lines.map((line) => {
            const remaining = Number(line.quantity) - Number(line.received_qty);
            return `
                <div class="form-row" data-line="${line.id}">
                    <div class="form-group">
                        <label>${escapeHtml(line.product_name)}</label>
                        <input value="Reste ${remaining}" disabled>
                    </div>
                    <div class="form-group">
                        <label>Quantité reçue</label>
                        <input class="receive-qty" type="number" min="0" max="${remaining}" step="0.01" value="${remaining > 0 ? remaining : 0}" ${remaining > 0 ? "" : "disabled"}>
                    </div>
                </div>`;
        }).join("") + `<button class="btn-primary" type="submit">Valider la réception</button>`;
        form.onsubmit = async (event) => {
            event.preventDefault();
            const lines = [...form.querySelectorAll("[data-line]")].map((row) => ({
                line_id: Number(row.dataset.line),
                quantity: Number(row.querySelector(".receive-qty").value),
            })).filter((line) => line.quantity > 0);
            if (!lines.length) {
                alert("Indiquez une quantité reçue.");
                return;
            }
            const res = await fetch(`${API}/purchases/orders/${order.id}/receive`, {
                method: "POST",
                headers: authHeaders(true),
                body: JSON.stringify({ lines }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                alert(apiError(data, "Réception impossible."));
                return;
            }
            closeModal("receive-modal");
            await loadAll();
        };
        openModal("receive-modal");
    }

    loadAll();
});
