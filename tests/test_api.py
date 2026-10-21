import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.services.seed_rbac import seed_tenant_rbac

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_whoami():
    response = client.get("/whoami", headers={"X-Tenant-ID": "test_tenant"})
    assert response.status_code == 200
    assert "test_tenant" in response.json()["message"]


def test_auth_and_protected_flow():
    email = f"admin_test_{__import__('uuid').uuid4().hex[:6]}@example.com"
    reg_payload = {
        "tenant_id": "tenant_alpha",
        "email": email,
        "password": "Password123!",
        "user_type": "admin"
    }
    reg_res = client.post("/auth/register", json=reg_payload)
    assert reg_res.status_code in [201, 400]

    login_res = client.post(
        "/auth/login",
        data={"username": email, "password": "Password123!"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "tenant_alpha"
    }

    dash_res = client.get("/admin/dashboard", headers=headers)
    assert dash_res.status_code == 200

    prod_payload = {
        "name": "Produit Test",
        "description": "Description test",
        "price": 15000.0,
        "stock": 10
    }
    prod_create = client.post("/products/", json=prod_payload, headers=headers)
    assert prod_create.status_code == 201
    prod_id = prod_create.json()["id"]

    prod_list = client.get("/products/", headers=headers)
    assert prod_list.status_code == 200
    assert any(p["id"] == prod_id for p in prod_list.json())

    del_res = client.delete(f"/products/{prod_id}", headers=headers)
    assert del_res.status_code == 204


def test_invoices_flow():
    headers = {"X-Tenant-ID": "tenant_alpha"}
    invoice_payload = {
        "doc_type": "INVOICE",
        "language": "fr",
        "payment_terms": "Paiement à 30 jours",
        "issuer": {
            "name": "Nexa Tech",
            "address": "Lomé, Togo",
            "phone": "+22890000000",
            "email": "contact@nexatech.com",
            "tax_id": "TG-12345",
            "issuing_place": "Lomé"
        },
        "customer": {
            "name": "Client VIP",
            "address": "Paris, France",
            "phone": "+33123456789",
            "email": "client@vip.com"
        },
        "items": [
            {
                "product_name": "Service Cloud",
                "unit": "Mois",
                "quantity": 2,
                "unit_price_ht": 50000.0,
                "tva_rate": 18.0,
                "discount": 0.0
            }
        ]
    }
    create_res = client.post("/invoices/", json=invoice_payload, headers=headers)
    assert create_res.status_code == 201
    invoice_data = create_res.json()
    assert invoice_data["total_ht"] == 100000.0
    assert invoice_data["tax_amount"] == 18000.0
    assert invoice_data["total_ttc"] == 118000.0
    invoice_id = invoice_data["id"]

    # Test PDF generation endpoint
    pdf_res = client.get(f"/invoices/{invoice_id}/pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 100


def test_warehouse_flow():
    headers = {"X-Tenant-ID": "tenant_alpha"}
    wh_payload = {
        "name": "Entrepôt Principal",
        "code": f"WH-{__import__('uuid').uuid4().hex[:4].upper()}",
        "location": "Zone Portuaire"
    }
    wh_res = client.post("/warehouses/", json=wh_payload, headers=headers)
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]

    # Stock Movement
    move_payload = {
        "warehouse_id": wh_id,
        "product_name": "Ordinateur Portable",
        "movement_type": "in",
        "quantity": 25.0,
        "reference": "BL-001"
    }
    move_res = client.post("/warehouses/stock/movements", json=move_payload, headers=headers)
    assert move_res.status_code == 201
    assert move_res.json()["quantity"] == 25.0


def test_ai_query():
    headers = {"X-Tenant-ID": "tenant_alpha"}
    ai_payload = {
        "prompt": "Quel est le chiffre d'affaires ?",
        "language": "fr"
    }
    ai_res = client.post("/ai/query", json=ai_payload, headers=headers)
    assert ai_res.status_code == 200
    data = ai_res.json()
    assert "answer" in data
    assert "metrics_summary" in data
    assert "suggested_actions" in data


def test_seed_rbac():
    db = SessionLocal()
    try:
        role = seed_tenant_rbac(db, tenant_id="test_rbac_tenant")
        assert role is not None
        assert role.name == "Responsable Commercial"
        assert len(role.permissions) >= 3
    finally:
        db.close()
