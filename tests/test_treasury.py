import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _company(prefix):
    suffix = uuid.uuid4().hex[:8]
    email = f"{prefix}-{suffix}@example.com"
    password = "password123"
    assert client.post("/auth/register", json={
        "tenant_id": f"{prefix}-{suffix}",
        "email": email,
        "password": password,
        "user_type": "admin",
        "company_name": prefix,
    }).status_code == 201
    login = client.post("/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _invoice(headers, amount=1000):
    response = client.post("/invoices/", json={
        "doc_type": "INVOICE",
        "language": "fr",
        "payment_terms": "Comptant",
        "issuer": {
            "name": "Nexa", "address": "Lomé", "phone": "90000000",
            "email": "contact@nexa.tg", "tax_id": "TG-1", "issuing_place": "Lomé",
        },
        "customer": {"name": "Client Test", "address": "Lomé", "phone": "91000000"},
        "items": [{"product_name": "Prestation", "unit": "u", "quantity": 1, "unit_price_ht": amount, "tva_rate": 0, "discount": 0}],
    }, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_treasury_collects_invoices_and_stays_isolated():
    owner = _company("treso")
    other = _company("autre-treso")
    invoice = _invoice(owner, 1000)

    partial = client.post(f"/invoices/{invoice['id']}/payments", json={"method": "cash", "amount": 400}, headers=owner)
    assert partial.status_code == 200
    assert partial.json()["remaining"] == 600
    assert partial.json()["status"] == "DRAFT"

    done = client.post(f"/invoices/{invoice['id']}/payments", json={"method": "bank_transfer", "amount": 600}, headers=owner)
    assert done.status_code == 200
    assert done.json()["status"] == "PAID"

    too_much = client.post(f"/invoices/{invoice['id']}/payments", json={"method": "cash", "amount": 1}, headers=owner)
    assert too_much.status_code == 422

    hidden = client.post(f"/invoices/{invoice['id']}/payments", json={"method": "cash", "amount": 1}, headers=other)
    assert hidden.status_code == 404

    manual = client.post("/treasury/movements", json={
        "direction": "out", "amount": 150, "method": "cash", "label": "Fournitures", "party_name": "Papeterie",
    }, headers=owner)
    assert manual.status_code == 201
    body = manual.json()
    assert body["cash_in"] == 1000
    assert body["cash_out"] == 150
    assert body["balance"] == 850
    assert body["open_invoices"] == []
    assert client.get("/treasury/overview", headers=other).json()["movements"] == []

    online = client.post(f"/invoices/{invoice['id']}/online-payment", json={}, headers=owner)
    assert online.status_code == 422
