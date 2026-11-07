const API = window.API || "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
    const token = sessionStorage.getItem("access_token") || localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    const STATUS = {
        envoye: "Envoyée",
        non_configure: "Canal à configurer",
        destinataire_absent: "Destinataire manquant",
        desactive: "Désactivée",
        echec: "Échec",
    };
    const CHANNEL = { email: "Email", sms: "SMS", whatsapp: "WhatsApp", telegram: "Telegram" };
    const EVENT = { login_success: "Connexion réussie", login_failure: "Connexion refusée", activity: "Activité" };

    const companyContext = document.getElementById("company-context");
    if (companyContext && window.NexaTenant) {
        const sessionUser = window.NexaTenant.getCurrentUser();
        const companyName = sessionUser.company_name || sessionUser.tenant_id || "votre entreprise";
        companyContext.textContent = `Entreprise connectée : ${companyName}. L'historique et les alertes ci-dessous concernent uniquement cet espace.`;
    }

    function headers(json) {
        const value = { Authorization: `Bearer ${token}` };
        if (json) value["Content-Type"] = "application/json";
        return value;
    }
    function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }
    function showTab(name) {
        ["connections", "activities", "notifications", "settings"].forEach((tab) => {
            document.getElementById(`panel-${tab}`).hidden = tab !== name;
            document.querySelector(`[data-tab="${tab}"]`).classList.toggle("active", tab === name);
        });
    }
    document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", () => showTab(button.dataset.tab)));

    async function load() {
        const [overviewRes, connectionRes, activityRes, notificationRes, profileRes] = await Promise.all([
            fetch(`${API}/security/overview`, { headers: headers() }),
            fetch(`${API}/security/connections`, { headers: headers() }),
            fetch(`${API}/security/activities`, { headers: headers() }),
            fetch(`${API}/security/notifications`, { headers: headers() }),
            fetch(`${API}/security/profile`, { headers: headers() }),
        ]);
        if ([overviewRes, connectionRes, activityRes, notificationRes, profileRes].some((res) => res.status === 401)) {
            window.location.href = "index.html";
            return;
        }
        const overview = overviewRes.ok ? await overviewRes.json() : { users: [], connections: 0, notifications: 0, policy: {}, company_scope: false };
        const profile = profileRes.ok ? await profileRes.json() : {};
        document.getElementById("kpi-users").textContent = overview.users.length;
        document.getElementById("kpi-connections").textContent = overview.connections;
        document.getElementById("kpi-notifications").textContent = overview.notifications;
        const withActivity = overview.users.filter((user) => user.last_activity_at).length;
        document.getElementById("kpi-active").textContent = withActivity;

        document.getElementById("users-body").innerHTML = overview.users.map((user) => `
            <tr>
                <td>${escapeHtml(user.full_name || user.email)}</td>
                <td>${escapeHtml(user.email)}</td>
                <td>${user.last_login_at ? new Date(user.last_login_at + "Z").toLocaleString("fr-FR") : "—"}</td>
                <td>${user.last_activity_at ? new Date(user.last_activity_at + "Z").toLocaleString("fr-FR") : "—"}</td>
                <td>${escapeHtml(user.last_login_ip || "—")}</td>
            </tr>`).join("") || `<tr><td colspan="5">Aucune connexion enregistrée.</td></tr>`;

        const connections = connectionRes.ok ? await connectionRes.json() : [];
        document.getElementById("connections-body").innerHTML = connections.map((row) => `
            <tr>
                <td>${escapeHtml(row.date)}</td>
                <td>${escapeHtml(row.time)}</td>
                <td>${escapeHtml(row.email)}</td>
                <td>${escapeHtml(EVENT[row.event_type] || row.event_type)}</td>
                <td>${escapeHtml(row.ip_address || "—")}</td>
            </tr>`).join("") || `<tr><td colspan="5">Aucune connexion.</td></tr>`;

        const activities = activityRes.ok ? await activityRes.json() : [];
        document.getElementById("activities-body").innerHTML = activities.map((row) => `
            <tr>
                <td>${escapeHtml(row.date)} ${escapeHtml(row.time)}</td>
                <td>${escapeHtml(row.email)}</td>
                <td>${escapeHtml(EVENT[row.event_type] || row.event_type)}</td>
                <td>${escapeHtml([row.method, row.resource].filter(Boolean).join(" ") || row.detail || "—")}</td>
            </tr>`).join("") || `<tr><td colspan="4">Aucune activité.</td></tr>`;

        const notifications = notificationRes.ok ? await notificationRes.json() : [];
        document.getElementById("notifications-body").innerHTML = notifications.map((row) => `
            <tr>
                <td>${row.created_at ? new Date(row.created_at + "Z").toLocaleString("fr-FR") : "—"}</td>
                <td>${escapeHtml(row.email)}</td>
                <td>${escapeHtml(CHANNEL[row.channel] || row.channel)}</td>
                <td>${escapeHtml(STATUS[row.status] || row.status)}</td>
                <td>${escapeHtml(row.provider_detail || "")}</td>
            </tr>`).join("") || `<tr><td colspan="5">Aucune notification.</td></tr>`;

        document.getElementById("phone").value = profile.phone || "";
        document.getElementById("telegram").value = profile.telegram_chat_id || "";
        document.getElementById("notify-email").checked = profile.notify_email !== false;
        document.getElementById("notify-sms").checked = profile.notify_sms !== false;
        document.getElementById("notify-whatsapp").checked = profile.notify_whatsapp !== false;
        document.getElementById("notify-telegram").checked = profile.notify_telegram !== false;

        const policyBox = document.getElementById("policy-box");
        policyBox.hidden = !overview.company_scope;
        const policy = overview.policy || {};
        document.getElementById("policy-email").checked = !!policy.email_enabled;
        document.getElementById("policy-sms").checked = !!policy.sms_enabled;
        document.getElementById("policy-whatsapp").checked = !!policy.whatsapp_enabled;
        document.getElementById("policy-telegram").checked = !!policy.telegram_enabled;
    }

    document.getElementById("profile-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const res = await fetch(`${API}/security/profile`, {
            method: "PUT",
            headers: headers(true),
            body: JSON.stringify({
                phone: document.getElementById("phone").value.trim(),
                telegram_chat_id: document.getElementById("telegram").value.trim(),
                notify_email: document.getElementById("notify-email").checked,
                notify_sms: document.getElementById("notify-sms").checked,
                notify_whatsapp: document.getElementById("notify-whatsapp").checked,
                notify_telegram: document.getElementById("notify-telegram").checked,
            }),
        });
        if (!res.ok) {
            alert("Enregistrement refusé.");
            return;
        }
        await load();
        showTab("settings");
    });

    document.getElementById("save-policy").addEventListener("click", async () => {
        const res = await fetch(`${API}/security/policy`, {
            method: "PUT",
            headers: headers(true),
            body: JSON.stringify({
                email_enabled: document.getElementById("policy-email").checked,
                sms_enabled: document.getElementById("policy-sms").checked,
                whatsapp_enabled: document.getElementById("policy-whatsapp").checked,
                telegram_enabled: document.getElementById("policy-telegram").checked,
            }),
        });
        if (!res.ok) {
            alert("Seul l'administrateur peut modifier les canaux de l'entreprise.");
            return;
        }
        await load();
        showTab("settings");
    });

    load();
});
