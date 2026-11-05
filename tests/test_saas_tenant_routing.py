import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_central_registry_routes_login_to_its_tenant_database():
    import uuid
    suffix = uuid.uuid4().hex[:8]
    tenant = f"lot1-{suffix}"
    email = f"Owner-{suffix}@example.com"
    password = "StrongPassword123!"

    registered = client.post("/auth/register", json={
        "tenant_id": tenant,
        "email": email,
        "password": password,
        "user_type": "admin",
    })
    assert registered.status_code == 201, registered.text
    assert registered.json()["email"] == email.lower()

    login = client.post("/auth/login", data={"username": email.upper(), "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    whoami = client.get("/whoami", headers=headers)
    assert whoami.status_code == 200, whoami.text
    assert whoami.json()["message"].endswith(tenant)


def test_tenant_header_cannot_override_signed_jwt_tenant():
    import uuid
    suffix = uuid.uuid4().hex[:8]
    tenant = f"jwt-{suffix}"
    other = f"other-{suffix}"
    email = f"owner-{suffix}@example.com"
    password = "StrongPassword123!"

    assert client.post("/auth/register", json={"tenant_id": tenant, "email": email, "password": password, "user_type": "admin"}).status_code == 201
    assert client.post("/auth/register", json={"tenant_id": other, "email": f"other-{suffix}@example.com", "password": password, "user_type": "admin"}).status_code == 201
    token = client.post("/auth/login", data={"username": email, "password": password}).json()["access_token"]

    response = client.get("/whoami", headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": other})
    assert response.status_code == 200
    assert response.json()["message"].endswith(tenant)


def test_tenant_identifier_validation_rejects_path_characters():
    from app.core.tenant_db import normalize_tenant_id
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        normalize_tenant_id("../outside")
