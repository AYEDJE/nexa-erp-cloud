const API = window.API || 'http://127.0.0.1:8000';

document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    const tr = (k, p) => (window.i18n ? window.i18n.t(k, p) : k);
    const isDemo = !token || token.startsWith("demo_");
    const COMPANY_KEY = "company_profile";

    const form = document.getElementById("company-form");
    const saveBtn = document.getElementById("co-save");
    const alertBox = document.getElementById("co-alert");
    const completeness = document.getElementById("co-completeness");

    // champ API -> id de l'input
    const FIELDS = {
        name: "co-name", legal_form: "co-legal-form", activity: "co-activity",
        address: "co-address", city: "co-city", country: "co-country",
        phone: "co-phone", email: "co-email", website: "co-website",
        tax_id: "co-tax-id", ice: "co-ice", ic: "co-ic", issuing_place: "co-place",
        default_tva_rate: "co-tva", payment_terms: "co-terms",
        bank_name: "co-bank", rib: "co-rib", iban: "co-iban", swift: "co-swift"
    };

    // Champs exigés par le backend pour émettre une facture
    const REQUIRED = {
        name: "Raison sociale", address: "Adresse", phone: "Téléphone",
        email: "Email", tax_id: "Matricule fiscal", issuing_place: "Lieu d'émission"
    };

    function formatApiError(data, fallback) {
        if (!data) return fallback;
        const d = data.detail !== undefined ? data.detail : (data.message !== undefined ? data.message : data);
        if (typeof d === "string") return d;
        if (Array.isArray(d)) {
            return d.map(e => {
                if (typeof e === "string") return e;
                const field = Array.isArray(e.loc) ? e.loc.filter(x => x !== "body").join(" → ") : "";
                return (field ? field + " : " : "") + (e.msg || JSON.stringify(e));
            }).join("\n");
        }
        try { return JSON.stringify(d); } catch (_) { return fallback; }
    }

    function showAlert(msg, type) {
        alertBox.textContent = msg;
        alertBox.className = type;
        alertBox.style.display = "block";
        if (type === "success") setTimeout(() => { alertBox.style.display = "none"; }, 4000);
    }

    function readForm() {
        const out = {};
        Object.entries(FIELDS).forEach(([key, id]) => {
            const v = (document.getElementById(id)?.value || "").trim();
            if (key === "default_tva_rate") out[key] = v === "" ? 19 : parseFloat(v);
            else out[key] = v === "" ? null : v;
        });
        return out;
    }

    function fillForm(c) {
        Object.entries(FIELDS).forEach(([key, id]) => {
            const el = document.getElementById(id);
            if (el) el.value = c[key] ?? (key === "default_tva_rate" ? 19 : "");
        });
        updateCompleteness(c);
    }

    function updateCompleteness(c) {
        const missing = Object.entries(REQUIRED).filter(([k]) => !c[k] || !String(c[k]).trim()).map(([, label]) => tr(label));
        completeness.style.display = "flex";
        if (missing.length === 0) {
            completeness.className = "completeness ok";
            completeness.innerHTML = `<i class="fa-solid fa-circle-check"></i><div>${tr("Profil complet : vous pouvez émettre des factures.")}</div>`;
        } else {
            completeness.className = "completeness warn";
            completeness.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i><div><strong>${tr("Profil incomplet")}</strong> — ${tr("à renseigner pour émettre des factures :")} ${missing.join(", ")}.</div>`;
        }
    }

    // Garde une copie locale isolée par entreprise (multi-tenant)
    function cacheProfile(c) {
        const clean = Object.fromEntries(Object.entries(c).filter(([, v]) => v !== null && v !== ""));
        if (window.NexaTenant) {
            window.NexaTenant.setData("company", clean);
        } else {
            localStorage.setItem(COMPANY_KEY, JSON.stringify(clean));
        }
    }

    async function loadCompany() {
        // Mode Démo ou Local isolé par entreprise
        if (isDemo || window.NexaTenant) {
            let data = null;
            if (window.NexaTenant) {
                data = window.NexaTenant.getData("company", null);
            }
            if (!data) {
                try { data = JSON.parse(localStorage.getItem(COMPANY_KEY)) || {}; } catch (_) { data = {}; }
            }
            // Si le profil est vide, pré-remplir avec les informations de l'entreprise connectée
            const u = window.NexaTenant ? window.NexaTenant.getCurrentUser() : null;
            if (u && (!data || !data.name)) {
                data = data || {};
                data.name = u.company_name || u.company || "";
                data.email = u.email || "";
            }
            fillForm(data || {});
            if (isDemo) return;
        }

        try {
            const res = await fetch(`${API}/company/`, { headers: { "Authorization": `Bearer ${token}` } });
            if (res.status === 401) {
                localStorage.removeItem("access_token");
                window.location.href = "index.html";
                return;
            }
            if (res.status === 403) throw new Error("Accès refusé : votre compte n'a pas le droit de consulter la société.");
            if (!res.ok) {
                const errData = await res.json().catch(() => null);
                throw new Error(formatApiError(errData, `Erreur ${res.status}`));
            }
            const company = await res.json();
            fillForm(company);
            cacheProfile(company);
        } catch (err) {
            console.warn("Connexion API indisponible pour la société, utilisation du profil isolé local :", err);
        }
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        alertBox.style.display = "none";

        const payload = readForm();

        // Contrôle avant envoi
        if (!payload.name) {
            showAlert(tr("La raison sociale est obligatoire."), "error");
            document.getElementById("co-name").focus();
            return;
        }

        if (isDemo) {
            cacheProfile(payload);
            updateCompleteness(payload);
            showAlert("Informations de la société enregistrées avec succès.", "success");
            return;
        }

        saveBtn.disabled = true;
        try {
            const res = await fetch(`${API}/company/`, {
                method: "PUT",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify(payload)
            });

            if (res.status === 401) {
                localStorage.removeItem("access_token");
                window.location.href = "index.html";
                return;
            }
            if (res.status === 403) throw new Error("Accès refusé : seul un administrateur peut modifier les informations de la société.");
            if (!res.ok) {
                const errData = await res.json().catch(() => null);
                console.error("Réponse API (société) :", res.status, errData, payload);
                throw new Error(formatApiError(errData, `Erreur ${res.status}`));
            }

            const saved = await res.json();
            fillForm(saved);
            cacheProfile(saved);
            showAlert("Informations de la société enregistrées avec succès.", "success");
        } catch (err) {
            console.warn("Backend indisponible, enregistrement local isolé pour cette entreprise :", err);
            cacheProfile(payload);
            updateCompleteness(payload);
            showAlert("Informations de la société enregistrées avec succès (espace entreprise isolé).", "success");
        } finally {
            saveBtn.disabled = false;
        }
    });

    loadCompany();
});
