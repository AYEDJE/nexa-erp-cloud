import os
import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _company(prefix):
    suffix = uuid.uuid4().hex[:8]
    email = f"{prefix}-{suffix}@example.com"
    tenant = f"{prefix}-{suffix}"
    assert client.post("/auth/register", json={
        "tenant_id": tenant,
        "email": email,
        "password": "password123",
        "user_type": "admin",
        "company_name": prefix,
    }).status_code == 201
    login = client.post("/auth/login", data={"username": email, "password": "password123"})
    assert login.status_code == 200
    return email, {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_login_history_activity_and_notifications_stay_inside_the_company():
    email, owner = _company("trace")
    _, other = _company("trace-autre")

    failed = client.post("/auth/login", data={"username": email, "password": "mauvais"})
    assert failed.status_code == 401

    connections = client.get("/security/connections", headers=owner).json()
    assert [row["event_type"] for row in connections][:2] == ["login_failure", "login_success"]
    assert connections[0]["date"] and connections[0]["time"]
    assert connections[0]["email"] == email
    assert email not in {row["email"] for row in client.get("/security/connections", headers=other).json()}

    created = client.post("/products/", json={"name": "Registre", "price": 100, "stock": 1}, headers=owner)
    assert created.status_code in {200, 201}
    activities = client.get("/security/activities", headers=owner).json()
    assert any(row["event_type"] == "activity" and row["resource"] == "/products/" for row in activities)

    overview = client.get("/security/overview", headers=owner).json()
    assert overview["company_scope"] is True
    assert overview["users"][0]["last_login_at"]
    assert overview["users"][0]["last_activity_at"]

    notes = client.get("/security/notifications", headers=owner).json()
    first_login = [row for row in notes if row["email"] == email]
    assert {row["channel"] for row in first_login} == {"email", "sms", "whatsapp", "telegram"}
    by_channel = {}
    for row in first_login:
        by_channel.setdefault(row["channel"], row)
    assert by_channel["sms"]["status"] == "destinataire_absent"
    assert by_channel["whatsapp"]["status"] == "destinataire_absent"
    assert by_channel["telegram"]["status"] == "destinataire_absent"
    if not os.getenv("SECURITY_SMTP_HOST"):
        assert by_channel["email"]["status"] == "non_configure"
    assert email not in {row["email"] for row in client.get("/security/notifications", headers=other).json()}

    assert client.put("/security/profile", json={
        "phone": "+22890000000",
        "telegram_chat_id": "10001",
        "notify_email": True,
        "notify_sms": True,
        "notify_whatsapp": False,
        "notify_telegram": True,
    }, headers=owner).status_code == 200
    assert client.put("/security/policy", json={
        "email_enabled": True,
        "sms_enabled": False,
        "whatsapp_enabled": True,
        "telegram_enabled": True,
    }, headers=owner).status_code == 200

    again = client.post("/auth/login", data={"username": email, "password": "password123"})
    assert again.status_code == 200
    owner = {"Authorization": f"Bearer {again.json()['access_token']}"}
    latest = {}
    for row in client.get("/security/notifications", headers=owner).json():
        latest.setdefault(row["channel"], row)
    assert latest["sms"]["status"] == "desactive"
    assert latest["whatsapp"]["status"] == "desactive"
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        assert latest["telegram"]["status"] == "non_configure"
        assert latest["telegram"]["destination"] == "10001"


def test_staff_only_sees_their_own_trace():
    _, admin = _company("trace-admin")
    suffix = uuid.uuid4().hex[:8]
    staff_email = f"collab-{suffix}@example.com"
    created = client.post("/users/", json={
        "email": staff_email,
        "password": "password123",
        "full_name": "Collaborateur",
        "user_type": "staff",
    }, headers=admin)
    assert created.status_code == 201
    login = client.post("/auth/login", data={"username": staff_email, "password": "password123"})
    assert login.status_code == 200
    staff = {"Authorization": f"Bearer {login.json()['access_token']}"}

    visible = {row["email"] for row in client.get("/security/connections", headers=staff).json()}
    assert visible == {staff_email}
    assert client.put("/security/policy", json={
        "email_enabled": False, "sms_enabled": False, "whatsapp_enabled": False, "telegram_enabled": False,
    }, headers=staff).status_code == 403
    admin_view = {row["email"] for row in client.get("/security/connections", headers=admin).json()}
    assert staff_email in admin_view
