const API = window.API || "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
    const token = sessionStorage.getItem("access_token") || localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    let warehouses = [];
    let stock = [];
    let movements = [];
    let products = [];
    const TYPES = { in: "Entrée", out: "Sortie", adjustment: "Ajustement" };

    const companyContext = document.getElementById("company-context");
    if (companyContext && window.NexaTenant) {
        const sessionUser = window.NexaTenant.getCurrentUser();
        const companyName = sessionUser.company_name || sessionUser.tenant_id || "votre entreprise";
        companyContext.textContent = `Entreprise connectée : ${companyName}. Les entrepôts et les quantités ci-dessous appartiennent uniquement à cet espace. Une réception d'achat crée une entrée.`;
    }

    function headers(json) {
        const value = { Authorization: `Bearer ${token}` };
        if (json) value["Content-Type"] = "application/json";
        return value;
    }
    function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }
    function apiError(data, fallback) {
        return data && typeof data.detail === "string" ? data.detail : fallback;
    }
    function warehouseName(id) {
        const warehouse = warehouses.find((item) => item.id === id);
        return warehouse ? warehouse.name : "Entrepôt";
    }
    function showTab(name) {
        ["stock", "warehouses", "movements"].forEach((tab) => {
            document.getElementById(`panel-${tab}`).hidden = tab !== name;
        });
        document.querySelectorAll(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === name));
    }
    document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", () => showTab(button.dataset.tab)));
    document.querySelectorAll("[data-close]").forEach((button) => {
        button.addEventListener("click", () => { document.getElementById(button.dataset.close).style.display = "none"; });
    });

    function fillWarehouseSelects() {
        const options = warehouses.map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("");
        ["mv-warehouse", "tr-from", "tr-to"].forEach((id) => { document.getElementById(id).innerHTML = options; });
        const productOptions = [`<option value="">Saisie libre</option>`]
            .concat(products.map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`))
            .join("");
        document.getElementById("mv-product").innerHTML = productOptions;
        document.getElementById("tr-product").innerHTML = productOptions;
    }

    function render() {
        document.getElementById("kpi-warehouses").textContent = String(warehouses.length);
        const positive = stock.filter((item) => Number(item.available_quantity) > 0);
        document.getElementById("kpi-items").textContent = String(positive.length);
        document.getElementById("kpi-units").textContent = String(positive.reduce((sum, item) => sum + Number(item.available_quantity), 0));
        document.getElementById("kpi-low").textContent = String(stock.filter((item) => Number(item.available_quantity) < 5).length);
        document.getElementById("stock-body").innerHTML = stock.length ? stock.map((item) => {
            const qty = Number(item.available_quantity);
            const level = qty <= 0 ? "empty" : qty < 5 ? "low" : "ok";
            const label = qty <= 0 ? "Rupture" : qty < 5 ? "Stock bas" : "Disponible";
            return `<tr>
                <td>${escapeHtml(item.product_name)}</td>
                <td>${escapeHtml(warehouseName(item.warehouse_id))}</td>
                <td>${item.total_in}</td>
                <td>${item.total_out}</td>
                <td><span class="pill ${level}">${qty} · ${label}</span></td>
            </tr>`;
        }).join("") : `<tr><td colspan="5" style="text-align:center;padding:24px;">Aucun stock. Créez un entrepôt, puis une entrée.</td></tr>`;
        document.getElementById("warehouses-body").innerHTML = warehouses.length ? warehouses.map((item) => `
            <tr><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.code)}</td><td>${escapeHtml(item.location || "—")}</td></tr>
        `).join("") : `<tr><td colspan="3" style="text-align:center;padding:24px;">Aucun entrepôt.</td></tr>`;
        document.getElementById("movements-body").innerHTML = movements.length ? movements.map((item) => `
            <tr>
                <td>${escapeHtml(String(item.created_at || "").slice(0, 16).replace("T", " "))}</td>
                <td>${escapeHtml(item.warehouse_name || warehouseName(item.warehouse_id))}</td>
                <td>${escapeHtml(item.product_name)}</td>
                <td>${TYPES[item.movement_type] || item.movement_type}</td>
                <td>${item.quantity}</td>
                <td>${escapeHtml(item.reference || item.notes || "—")}</td>
            </tr>
        `).join("") : `<tr><td colspan="6" style="text-align:center;padding:24px;">Aucun mouvement.</td></tr>`;
        fillWarehouseSelects();
    }

    async function load() {
        const [warehouseRes, stockRes, movementRes, productRes] = await Promise.all([
            fetch(`${API}/warehouses/`, { headers: headers() }),
            fetch(`${API}/warehouses/stock`, { headers: headers() }),
            fetch(`${API}/warehouses/stock/movements`, { headers: headers() }),
            fetch(`${API}/products/`, { headers: headers() }),
        ]);
        if ([warehouseRes, stockRes, movementRes].some((res) => res.status === 401)) {
            window.location.href = "index.html";
            return;
        }
        if (!warehouseRes.ok || !stockRes.ok || !movementRes.ok) {
            const failed = [warehouseRes, stockRes, movementRes].find((res) => !res.ok);
            const data = await failed.json().catch(() => ({}));
            document.getElementById("stock-body").innerHTML = `<tr><td colspan="5" style="color:#991b1b;padding:24px;">${escapeHtml(apiError(data, "Impossible de charger le stock."))}</td></tr>`;
            return;
        }
        warehouses = await warehouseRes.json();
        stock = await stockRes.json();
        movements = await movementRes.json();
        products = productRes.ok ? await productRes.json() : [];
        render();
    }

    function openModal(id) {
        document.getElementById(id).style.display = "block";
    }
    document.getElementById("open-warehouse").addEventListener("click", () => {
        document.getElementById("warehouse-form").reset();
        openModal("warehouse-modal");
    });
    document.getElementById("open-movement").addEventListener("click", () => {
        if (!warehouses.length) {
            alert("Créez d'abord un entrepôt.");
            return;
        }
        document.getElementById("movement-form").reset();
        openModal("movement-modal");
    });
    document.getElementById("open-transfer").addEventListener("click", () => {
        if (warehouses.length < 2) {
            alert("Il faut au moins deux entrepôts pour un transfert.");
            return;
        }
        document.getElementById("transfer-form").reset();
        openModal("transfer-modal");
    });

    document.getElementById("mv-product").addEventListener("change", (event) => {
        const product = products.find((item) => String(item.id) === event.target.value);
        if (product) document.getElementById("mv-name").value = product.name;
    });
    document.getElementById("tr-product").addEventListener("change", (event) => {
        const product = products.find((item) => String(item.id) === event.target.value);
        if (product) document.getElementById("tr-name").value = product.name;
    });

    document.getElementById("warehouse-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const res = await fetch(`${API}/warehouses/`, {
            method: "POST",
            headers: headers(true),
            body: JSON.stringify({
                name: document.getElementById("wh-name").value.trim(),
                code: document.getElementById("wh-code").value.trim(),
                location: document.getElementById("wh-location").value.trim(),
            }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            alert(apiError(data, "Entrepôt refusé."));
            return;
        }
        document.getElementById("warehouse-modal").style.display = "none";
        await load();
        showTab("warehouses");
    });

    document.getElementById("movement-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const productId = document.getElementById("mv-product").value;
        const res = await fetch(`${API}/warehouses/stock/movements`, {
            method: "POST",
            headers: headers(true),
            body: JSON.stringify({
                warehouse_id: Number(document.getElementById("mv-warehouse").value),
                product_id: productId ? Number(productId) : null,
                product_name: document.getElementById("mv-name").value.trim() || "Article",
                movement_type: document.getElementById("mv-type").value,
                quantity: Number(document.getElementById("mv-qty").value),
                notes: document.getElementById("mv-notes").value.trim(),
            }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            alert(apiError(data, "Mouvement refusé."));
            return;
        }
        document.getElementById("movement-modal").style.display = "none";
        await load();
        showTab("stock");
    });

    document.getElementById("transfer-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const productId = document.getElementById("tr-product").value;
        const res = await fetch(`${API}/warehouses/stock/transfers`, {
            method: "POST",
            headers: headers(true),
            body: JSON.stringify({
                from_warehouse_id: Number(document.getElementById("tr-from").value),
                to_warehouse_id: Number(document.getElementById("tr-to").value),
                product_id: productId ? Number(productId) : null,
                product_name: document.getElementById("tr-name").value.trim() || "Article",
                quantity: Number(document.getElementById("tr-qty").value),
            }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            alert(apiError(data, "Transfert refusé."));
            return;
        }
        document.getElementById("transfer-modal").style.display = "none";
        await load();
        showTab("stock");
    });

    load();
});
