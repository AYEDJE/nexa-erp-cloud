import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _company(prefix):
    suffix = uuid.uuid4().hex[:8]
    tenant = f"{prefix}-{suffix}"
    email = f"{prefix}-{suffix}@example.com"
    password = "password123"
    assert client.post("/auth/register", json={
        "tenant_id": tenant,
        "email": email,
        "password": password,
        "user_type": "admin",
        "company_name": prefix,
    }).status_code == 201
    login = client.post("/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_purchase_order_is_isolated_and_updates_stock():
    buyer = _company("achat")
    other = _company("autreachat")

    supplier = client.post("/purchases/suppliers", json={
        "name": "Fournitures Sahel",
        "email": "contact@sahel.example",
        "phone": "90000000",
    }, headers=buyer)
    assert supplier.status_code == 201
    supplier_id = supplier.json()["id"]

    product = client.post("/products/", json={"name": "Ramette A4", "price": 2500, "stock": 4}, headers=buyer)
    assert product.status_code == 201
    product_id = product.json()["id"]

    order = client.post("/purchases/orders", json={
        "supplier_id": supplier_id,
        "notes": "Réassort",
        "lines": [{
            "product_id": product_id,
            "product_name": "ignoré",
            "quantity": 10,
            "unit_price_ht": 2000,
            "tva_rate": 18,
        }],
    }, headers=buyer)
    assert order.status_code == 201
    body = order.json()
    assert body["status"] == "draft"
    assert body["lines"][0]["product_name"] == "Ramette A4"
    assert body["total_ttc"] == 23600
    order_id = body["id"]
    line_id = body["lines"][0]["id"]

    assert client.post(f"/purchases/orders/{order_id}/receive", json={
        "lines": [{"line_id": line_id, "quantity": 10}]
    }, headers=buyer).status_code == 422

    confirmed = client.post(f"/purchases/orders/{order_id}/confirm", headers=buyer)
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    partial = client.post(f"/purchases/orders/{order_id}/receive", json={
        "lines": [{"line_id": line_id, "quantity": 4}]
    }, headers=buyer)
    assert partial.status_code == 200
    assert partial.json()["status"] == "partial"

    done = client.post(f"/purchases/orders/{order_id}/receive", json={
        "lines": [{"line_id": line_id, "quantity": 6}]
    }, headers=buyer)
    assert done.status_code == 200
    assert done.json()["status"] == "received"

    stock = client.get("/products/", headers=buyer).json()
    ramette = next(item for item in stock if item["id"] == product_id)
    assert ramette["stock"] == 14

    assert client.get("/purchases/orders", headers=other).json() == []
    assert client.get("/purchases/suppliers", headers=other).json() == []
    hidden = client.post(f"/purchases/orders/{order_id}/cancel", headers=other)
    assert hidden.status_code == 404
