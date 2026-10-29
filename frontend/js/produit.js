const API = 'http://127.0.0.1:8000';

document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("access_token");
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

    const isDemo = token.startsWith("demo_");

    // Données de démonstration initiales (si mode démo)
    function getDemoProducts() {
        const stored = localStorage.getItem("demo_products");
        if (stored) return JSON.parse(stored);
        const defaults = [
            { id: 1, name: "Ordinateur Portable Pro 15\"", description: "Intel i7, 16GB RAM, 512GB SSD", price: 850.0, stock: 12 },
            { id: 2, name: "Écran 27\" 4K UHD", description: "Dalle IPS, USB-C, 60Hz", price: 320.0, stock: 8 },
            { id: 3, name: "Clavier Mécanique Sans Fil", description: "Switches tactiles silencieux", price: 89.90, stock: 25 },
            { id: 4, name: "Souris Ergonomique", description: "Capteur optique 4000 DPI", price: 45.0, stock: 3 },
            { id: 5, name: "Imprimante Laser Multifonction", description: "Wifi, Recto-verso automatique", price: 290.0, stock: 0 }
        ];
        localStorage.setItem("demo_products", JSON.stringify(defaults));
        return defaults;
    }

    // Récupérer la liste des produits
    async function fetchProducts() {
        if (isDemo) {
            renderTable(getDemoProducts());
            return;
        }

        try {
            const response = await fetch(`${API}/products/`, {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            if (response.status === 401) {
                // Session expirée
                localStorage.removeItem("access_token");
                window.location.href = "index.html";
                return;
            }

            if (!response.ok) throw new Error("Erreur de récupération");
            const products = await response.json();
            renderTable(products);
        } catch (error) {
            console.warn("Échec de connexion au serveur backend, passage temporaire en données démo locale :", error);
            renderTable(getDemoProducts());
        }
    }

    // Affichage dans le tableau
    function renderTable(products) {
        if (!products || products.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 24px; color: #6b7280;">Aucun produit trouvé. Cliquez sur "Nouveau Produit" pour en créer un.</td></tr>`;
            return;
        }

        tableBody.innerHTML = products.map(p => {
            const stockQty = p.stock !== undefined ? p.stock : (p.stock_quantity || 0);
            const stockBadgeClass = stockQty === 0 ? "badge-danger" : (stockQty <= 5 ? "badge-warning" : "badge-success");
            const stockLabel = stockQty === 0 ? "Rupture (0)" : `${stockQty} en stock`;

            return `
            <tr>
                <td><strong>#${p.id}</strong></td>
                <td><strong>${p.name}</strong></td>
                <td><small style="color:#6b7280;">${p.description || '—'}</small></td>
                <td><span style="font-weight:600; color:#1a73e8;">${Number(p.price).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €</span></td>
                <td><span class="stock-pill ${stockBadgeClass}">${stockLabel}</span></td>
                <td>
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

        if (isDemo) {
            // Mode Démo Local
            const demoList = getDemoProducts();
            const newId = demoList.length > 0 ? Math.max(...demoList.map(p => p.id)) + 1 : 1;
            demoList.push({ id: newId, ...productPayload });
            localStorage.setItem("demo_products", JSON.stringify(demoList));
            modal.style.display = "none";
            fetchProducts();
            return;
        }

        // Mode Backend Réel
        try {
            const response = await fetch(`${API}/products/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(productPayload)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Erreur lors de l'enregistrement");
            }

            modal.style.display = "none";
            fetchProducts();
        } catch (error) {
            console.error(error);
            alert("Erreur lors de la sauvegarde : " + error.message);
        }
    });

    // Suppression d'un produit
    async function handleDelete(id) {
        if (!confirm("Voulez-vous vraiment supprimer ce produit ?")) return;

        if (isDemo) {
            let demoList = getDemoProducts();
            demoList = demoList.filter(p => String(p.id) !== String(id));
            localStorage.setItem("demo_products", JSON.stringify(demoList));
            fetchProducts();
            return;
        }

        try {
            const response = await fetch(`${API}/products/${id}`, {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            if (!response.ok) throw new Error("Impossible de supprimer");
            fetchProducts();
        } catch (error) {
            console.error(error);
            alert("Erreur lors de la suppression du produit.");
        }
    }

    // Chargement initial
    fetchProducts();
});
