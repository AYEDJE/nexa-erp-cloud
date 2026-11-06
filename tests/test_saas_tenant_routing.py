import uuid

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _register(tenant, email):
    response = client.post("/auth/register", json={"tenant_id": tenant, "email": email, "password": "StrongPassword123!", "user_type": "admin"})
    assert response.status_code == 201, response.text


def _login(email):
    response = client.post("/auth/login", data={"username": email, "password": "StrongPassword123!"})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_tenant_header_cannot_override_jwt_database_routing():
    suffix = uuid.uuid4().hex[:8]
    tenant_a, tenant_b = f"alpha-{suffix}", f"beta-{suffix}"
    email_a, email_b = f"a-{suffix}@example.test", f"b-{suffix}@example.test"
    _register(tenant_a, email_a)
    _register(tenant_b, email_b)
    token_a = _login(email_a)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    created = client.post("/products/", json={"name": f"ONLY-A-{suffix}", "price": 1, "stock": 1}, headers=headers_a)
    assert created.status_code == 201, created.text

    # Header B is ignored for routing: tenant A still sees its own product.
    listed_a = client.get("/products/", headers={**headers_a, "X-Tenant-ID": tenant_b})
    assert listed_a.status_code == 200, listed_a.text
    assert any(item["name"] == f"ONLY-A-{suffix}" for item in listed_a.json())

    # Tenant B's independent database must not contain tenant A's record.
    token_b = _login(email_b)
    listed_b = client.get("/products/", headers={"Authorization": f"Bearer {token_b}", "X-Tenant-ID": tenant_a})
    assert listed_b.status_code == 200, listed_b.text
    assert all(item["name"] != f"ONLY-A-{suffix}" for item in listed_b.json())


def test_protected_tenant_route_rejects_header_without_jwt():
    response = client.get("/products/", headers={"X-Tenant-ID": "not-authorized"})
    assert response.status_code == 401
