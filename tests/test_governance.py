import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.tenant_db import get_tenant_sessionmaker
from app.main import app
from app.models.security import UserSessionORM

client = TestClient(app)


def _register(prefix):
    suffix = uuid.uuid4().hex[:8]
    email = f"{prefix}-{suffix}@example.com"
    assert client.post("/auth/register", json={
        "tenant_id": f"{prefix}-{suffix}",
        "email": email,
        "password": "password123",
        "user_type": "admin",
        "company_name": prefix,
    }).status_code == 201
    return email


def _login(email):
    response = client.post("/auth/login", data={"username": email, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_new_login_closes_the_previous_session_and_idle_timeout():
    email = _register("session")
    first = _login(email)
    second = _login(email)
    closed = client.get("/auth/session", headers={"Authorization": f"Bearer {first}"})
    assert closed.status_code == 401
    assert "fermée" in closed.json()["detail"]
    current = client.get("/auth/session", headers={"Authorization": f"Bearer {second}"})
    assert current.status_code == 200
    assert current.json()["open_sessions"] == 1
    assert current.json()["idle_minutes"] == 30

    payload = jwt.decode(second, SECRET_KEY, algorithms=[ALGORITHM])
    db = get_tenant_sessionmaker(payload["tenant_id"])()
    try:
        session = db.query(UserSessionORM).filter_by(session_token=payload["jti"]).one()
        session.last_active_at = datetime.utcnow() - timedelta(minutes=45)
        db.commit()
    finally:
        db.close()
    idle = client.get("/products/", headers={"Authorization": f"Bearer {second}"})
    assert idle.status_code == 401
    assert "inactivité" in idle.json()["detail"]


def test_role_blocks_unauthorised_module_and_backup_keeps_its_company():
    admin_email = _register("gouv")
    admin = {"Authorization": f"Bearer {_login(admin_email)}"}
    other_email = _register("gouv-autre")
    other = {"Authorization": f"Bearer {_login(other_email)}"}
    created = client.post("/users/", json={
        "email": f"magasin-{uuid.uuid4().hex[:6]}@example.com",
        "password": "password123",
        "full_name": "Magasinier",
        "role": "stock",
    }, headers=admin)
    assert created.status_code == 201
    staff = {"Authorization": f"Bearer {_login(created.json()['email'])}"}
    admin = {"Authorization": f"Bearer {_login(admin_email)}"}
    assert client.get("/warehouses/", headers=staff).status_code == 200
    forbidden = client.get("/invoices/", headers=staff)
    assert forbidden.status_code == 403
    assert "facturation" in forbidden.json()["detail"]

    for _ in range(3):
        assert client.post("/auth/login", data={"username": admin_email, "password": "mauvais"}).status_code == 401
    alerts = client.get("/admin/security/alerts", headers=admin).json()
    assert any(row["alert_type"] == "brute_force" for row in alerts)
    assert any(row["alert_type"] == "session_replaced" for row in alerts)

    snapshot = client.post("/admin/backups/export", headers=admin)
    assert snapshot.status_code == 200
    body = snapshot.json()
    assert len(body["metadata"]["checksum"]) == 64
    assert body["metadata"]["passwords_included"] is False
    assert "hashed_password" not in snapshot.text
    journal = client.get("/audit/logs", headers=admin).json()
    assert any(row["action"] == "BACKUP_EXPORT" and row["email"] == admin_email for row in journal)
    assert client.get("/audit/logs", headers=other).json() == [] or all(row["email"] != admin_email for row in client.get("/audit/logs", headers=other).json())

    tampered = json_copy(body)
    tampered["products"].append({"name": "Injecté", "price": 1, "stock": 1})
    assert client.post("/admin/backups/restore", json={"snapshot": tampered}, headers=admin).status_code == 400
    foreign = client.post("/admin/backups/restore", json={"snapshot": body}, headers=other)
    assert foreign.status_code == 400
    assert "autre entreprise" in foreign.json()["detail"]
    assert client.post("/admin/backups/restore", json={"snapshot": body}, headers=admin).status_code == 200


def json_copy(value):
    import json
    return json.loads(json.dumps(value))
