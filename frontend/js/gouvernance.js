const API = window.API || "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
    const token = sessionStorage.getItem("access_token") || localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }
    const headers = { Authorization: `Bearer ${token}` };
    function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }
    function showTab(name) {
        ["session", "journal", "backup"].forEach((tab) => {
            document.getElementById(`panel-${tab}`).hidden = tab !== name;
            document.querySelector(`[data-tab="${tab}"]`).classList.toggle("active", tab === name);
        });
    }
    document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", () => showTab(button.dataset.tab)));
    if (window.NexaTenant) {
        const user = window.NexaTenant.getCurrentUser();
        document.getElementById("company-context").textContent = `Entreprise connectée : ${user.company_name || user.tenant_id || "votre espace"}. Une seule session est autorisée par compte.`;
    }

    async function load() {
        const [sessionRes, alertRes, journalRes] = await Promise.all([
            fetch(`${API}/auth/session`, { headers }),
            fetch(`${API}/admin/security/alerts`, { headers }),
            fetch(`${API}/audit/logs`, { headers }),
        ]);
        if (sessionRes.status === 401) {
            window.location.href = "index.html";
            return;
        }
        const session = sessionRes.ok ? await sessionRes.json() : {};
        document.getElementById("kpi-sessions").textContent = session.open_sessions ?? 0;
        document.getElementById("kpi-idle").textContent = `${session.idle_minutes || 30} min`;
        document.getElementById("session-text").textContent = session.active
            ? `Cette connexion est la seule session active. Elle se ferme après ${session.idle_minutes || 30} minutes sans activité, ou dès qu'une nouvelle connexion utilise le même compte.`
            : "Aucune session active.";
        const alerts = alertRes.ok ? await alertRes.json() : [];
        document.getElementById("kpi-alerts").textContent = alerts.length;
        document.getElementById("alerts-body").innerHTML = alerts.map((row) => `
            <tr>
                <td>${escapeHtml(row.alert_type)}</td>
                <td>${escapeHtml(row.severity)}</td>
                <td>${escapeHtml(row.ip_address || "—")}</td>
                <td>${escapeHtml(row.details || "")}</td>
                <td>${row.created_at ? new Date(row.created_at).toLocaleString("fr-FR") : "—"}</td>
            </tr>`).join("") || `<tr><td colspan="5">Aucune alerte.</td></tr>`;
        const journal = journalRes.ok ? await journalRes.json() : [];
        document.getElementById("journal-body").innerHTML = journal.map((row) => `
            <tr>
                <td>${escapeHtml(row.date || "")}</td>
                <td>${escapeHtml(row.time || "")}</td>
                <td>${escapeHtml(row.email || "—")}</td>
                <td>${escapeHtml(row.action)}</td>
                <td>${escapeHtml(row.resource)}</td>
            </tr>`).join("") || `<tr><td colspan="5">${journalRes.ok ? "Aucune opération journalisée." : "Le journal est réservé à l'administrateur."}</td></tr>`;
    }

    document.getElementById("export-backup").addEventListener("click", async () => {
        const res = await fetch(`${API}/admin/backups/export`, { method: "POST", headers });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            document.getElementById("backup-message").textContent = data.detail || "Export refusé.";
            return;
        }
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `sauvegarde-${data.metadata.tenant_id}.json`;
        link.click();
        document.getElementById("backup-message").textContent = `Sauvegarde créée. Empreinte ${data.metadata.checksum.slice(0, 12)}…`;
        load();
    });

    document.getElementById("restore-file").addEventListener("change", async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        const snapshot = JSON.parse(await file.text());
        const res = await fetch(`${API}/admin/backups/restore`, {
            method: "POST",
            headers: { ...headers, "Content-Type": "application/json" },
            body: JSON.stringify({ snapshot }),
        });
        const data = await res.json().catch(() => ({}));
        document.getElementById("backup-message").textContent = res.ok
            ? "Restauration acceptée pour cette entreprise."
            : (data.detail || "Restauration refusée.");
        load();
    });

    load();
});
