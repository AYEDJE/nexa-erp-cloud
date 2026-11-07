import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _company(prefix):
    suffix = uuid.uuid4().hex[:8]
    email = f"{prefix}-{suffix}@example.com"
    assert client.post("/auth/register", json={
        "tenant_id": f"{prefix}-{suffix}",
        "email": email,
        "password": "password123",
        "user_type": "admin",
        "company_name": prefix,
    }).status_code == 201
    login = client.post("/auth/login", data={"username": email, "password": "password123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_invoice_created_in_one_company_is_invisible_to_the_other():
    owner = _company("facture-a")
    other = _company("facture-b")
    payload = {
        "doc_type": "INVOICE",
        "language": "fr",
        "payment_terms": "Virement",
        "issuer": {
            "name": "Entreprise A",
            "address": "Lomé",
            "phone": "+22890000000",
            "email": "a@example.com",
            "tax_id": "123",
            "issuing_place": "Lomé",
        },
        "customer": {"name": "Client privé A", "address": "Lomé", "phone": "+22891111111"},
        "items": [{"product_name": "Prestation", "unit": "U", "quantity": 1, "unit_price_ht": 100, "tva_rate": 18, "discount": 0}],
    }
    created = client.post("/invoices/", json=payload, headers=owner)
    assert created.status_code == 201
    number = created.json()["number"]
    own_list = client.get("/invoices/", headers=owner).json()
    assert [row["number"] for row in own_list] == [number]
    assert client.get("/invoices/", headers=other).json() == []
    assert client.get(f"/invoices/{created.json()['id']}", headers=other).status_code == 404
