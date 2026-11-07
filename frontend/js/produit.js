const API = 'http://127.0.0.1:8000';

document.addEventListener("DOMContentLoaded", () => {
    const token = sessionStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    const tableBody = document.getElementById("products-table-body");
    const modal = document.getElementById("product-modal");
    const openModalBtn = document.getElementById("open-add-modal");
    const closeModalBtn = document.getElementById("close-modal");
    const productForm = document.getElementById("product-form");
    const modalTitle = document.getElementById("modal-title");

    function getDefaultProductsForDemo() {
        return [
            { id: 1, name: "Ordinateur Portable Pro 15\"", description: "Intel i7, 16GB RAM, 512GB SSD", price: 850.0, stock: 12 },
            { id: 2, name: "Écran 27\" 4K UHD", description: "Dalle IPS, USB-C, 60Hz", price: 320.0, stock: 8 },
            { id: 3, name: "Clavier Mécanique Sans Fil", description: "Switches tactiles silencieux", price: 89.90, stock: 25 },
            { id: 4, name: "Souris Ergonomique", description: "Capteur optique 4000 DPI", price: 45.0, stock: 3 },
            { id: 5, name: "Imprimante Laser Multifonction", description: "Wifi, Recto-verso automatique", price: 290.0, stock: 0 }
        ];
    }

    // Récupération des produits strictement isolés par entreprise
    function getTenantProducts() {
        const tenantId = window.NexaTenant ? window.NexaTenant.getTenantId() : 'default';
        const isSeedDemo = (tenantId === 'entreprise_demo');
        const fallback = isSeedDemo ? getDefaultProductsForDemo() : [];

        if (window.NexaTenant) {
            return window.NexaTenant.getData('products', fallback);
        }
        const key = `nexa_${tenantId}_products`;
        const stored = localStorage.getItem(key);
        return stored ? JSON.parse(stored) : fallback;
    }

    function saveTenantProducts(list) {
        if (window.NexaTenant) {
            window.NexaTenant.setData('products', list);
        } else {
            const tenantId = 'default';
            localStorage.setItem(`nexa_${tenantId}_products`, JSON.stringify(list));
        }
    }

    // Récupérer la liste des produits
    async function fetchProducts() {
        // 1. Essayer le backend en premier (si disponible)
        try {
            const response = await fetch(`${API}/products/`, {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            if (response.status === 401) {
                localStorage.removeItem("access_token");
                window.location.href = "index.html";
                return;
            }

            if (response.ok) {
                const products = await response.json();
                saveTenantProducts(products);
                renderTable(products);
                return;
            }
        } catch (error) {
            // Backend offline -> passage au stockage local isolé du tenant
        }

        // 2. Mode local isolé pour l'entreprise
        renderTable(getTenantProducts());
    }

    // Affichage dans le tableau
    function renderTable(products) {
        const currentUser = window.NexaTenant ? window.NexaTenant.getCurrentUser() : {};
        const companyName = currentUser.company_name || currentUser.tenant_id || "votre entreprise";

        if (!products || products.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 28px; color: #64748b;">
                <i class="fa-solid fa-box-open" style="font-size:24px; color:#cbd5e1; margin-bottom:8px; display:block;"></i>
                Aucun produit au catalogue pour <strong>${escapeHtml(companyName)}</strong>.<br>
                <span style="font-size:12px;">Cliquez sur <strong>+ Nouveau Produit</strong> ci-dessus pour ajouter votre premier article.</span>
            </td></tr>`;
            return;
        }

        tableBody.innerHTML = products.map(p => {
            const stockQty = p.stock !== undefined ? p.stock : (p.stock_quantity || 0);
            const stockBadgeClass = stockQty === 0 ? "badge-danger" : (stockQty <= 5 ? "badge-warning" : "badge-success");
            const stockLabel = stockQty === 0 ? "Rupture (0)" : `${stockQty} en stock`;

            return `
            <tr>
                <td><strong>#${p.id}</strong></td>
                <td><strong>${escapeHtml(p.name)}</strong></td>
                <td><small style="color:#6b7280;">${escapeHtml(p.description || '—')}</small></td>
                <td><span style="font-weight:600; color:#1a73e8;">${Number(p.price).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €</span></td>
                <td><span class="stock-pill ${stockBadgeClass}">${stockLabel}</span></td>
                <td style="text-align:center;">
                    <button class="btn-icon delete-btn" data-id="${p.id}" title="Supprimer ce produit" style="color: #dc2626; cursor: pointer;">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            </tr>
            `;
        }).join("");

        // Écouteurs pour la suppression
        document.querySelectorAll(".delete-btn").forEach(btn => {
            btn.addEventListener("click", () => handleDelete(btn.dataset.id));
        });
    }

    function escapeHtml(text) {
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Ouvrir modale ajout
    if (openModalBtn) {
        openModalBtn.addEventListener("click", () => {
            productForm.reset();
            document.getElementById("product-id").value = "";
            modalTitle.textContent = "Ajouter un nouveau produit";
            modal.style.display = "block";
        });
    }

    // Fermer modale
    if (closeModalBtn) {
        closeModalBtn.addEventListener("click", () => {
            modal.style.display = "none";
        });
    }

    window.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
    });

    // Enregistrement d'un produit
    productForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const nameInput = document.getElementById("name").value.trim();
        const descInput = document.getElementById("description").value.trim();
        const priceInput = parseFloat(document.getElementById("price").value);
        const stockInput = parseInt(document.getElementById("stock").value, 10) || 0;

        if (!nameInput || isNaN(priceInput)) {
            alert("Veuillez renseigner un nom et un prix valide.");
            return;
        }

        const productPayload = {
            name: nameInput,
            description: descInput,
            price: priceInput,
            stock: stockInput
        };

        // Sauvegarde locale isolée pour l'entreprise
        const localList = getTenantProducts();
        const newId = localList.length > 0 ? Math.max(...localList.map(p => p.id)) + 1 : 1;
        localList.push({ id: newId, ...productPayload });
        saveTenantProducts(localList);

        // Tentative de synchronisation backend si connecté
        try {
            await fetch(`${API}/products/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(productPayload)
            });
        } catch (_) {}

        modal.style.display = "none";
        fetchProducts();
        alert(`✅ Produit « ${nameInput} » ajouté au catalogue de votre entreprise !`);
    });

    // Suppression d'un produit
    async function handleDelete(id) {
        if (!confirm("Voulez-vous vraiment supprimer ce produit ?")) return;

        let list = getTenantProducts();
        list = list.filter(p => String(p.id) !== String(id));
        saveTenantProducts(list);

        try {
            await fetch(`${API}/products/${id}`, {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });
        } catch (_) {}

        fetchProducts();
    }

    // Chargement initial
    fetchProducts();
});
