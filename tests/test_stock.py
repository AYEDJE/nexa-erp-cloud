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


def test_stock_is_isolated_and_blocks_oversell():
    owner = _company("stock")
    other = _company("autre-stock")
    warehouse = client.post("/warehouses/", json={"name": "Magasin Lomé", "code": "lom", "location": "Port"}, headers=owner)
    assert warehouse.status_code == 201
    assert warehouse.json()["code"] == "LOM"
    warehouse_id = warehouse.json()["id"]
    assert client.post("/warehouses/", json={"name": "Doublon", "code": "lom"}, headers=owner).status_code == 409

    product = client.post("/products/", json={"name": "Cahier", "price": 500, "stock": 0}, headers=owner)
    product_id = product.json()["id"]
    entered = client.post("/warehouses/stock/movements", json={
        "warehouse_id": warehouse_id,
        "product_id": product_id,
        "product_name": "ignoré",
        "movement_type": "in",
        "quantity": 10,
    }, headers=owner)
    assert entered.status_code == 201
    assert entered.json()["product_name"] == "Cahier"

    too_much = client.post("/warehouses/stock/movements", json={
        "warehouse_id": warehouse_id,
        "product_name": "Cahier",
        "movement_type": "out",
        "quantity": 11,
    }, headers=owner)
    assert too_much.status_code == 422

    left = client.post("/warehouses/stock/movements", json={
        "warehouse_id": warehouse_id,
        "product_id": product_id,
        "product_name": "Cahier",
        "movement_type": "out",
        "quantity": 4,
    }, headers=owner)
    assert left.status_code == 201

    second = client.post("/warehouses/", json={"name": "Annexe", "code": "ann"}, headers=owner).json()
    transfer = client.post("/warehouses/stock/transfers", json={
        "from_warehouse_id": warehouse_id,
        "to_warehouse_id": second["id"],
        "product_name": "Cahier",
        "quantity": 2,
    }, headers=owner)
    assert transfer.status_code == 201

    levels = {(row["warehouse_id"], row["product_name"]): row["available_quantity"] for row in client.get("/warehouses/stock", headers=owner).json()}
    assert levels[(warehouse_id, "Cahier")] == 4
    assert levels[(second["id"], "Cahier")] == 2
    assert client.get("/products/", headers=owner).json()[0]["stock"] == 6
    assert client.get("/warehouses/", headers=other).json() == []
    assert client.post("/warehouses/stock/movements", json={
        "warehouse_id": warehouse_id, "product_name": "Cahier", "movement_type": "out", "quantity": 1,
    }, headers=other).status_code == 404
