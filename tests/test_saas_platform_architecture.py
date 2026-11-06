import uuid

from fastapi.testclient import TestClient

from app.core.database import CentralSessionLocal
from app.core.tenant_db import get_tenant_sessionmaker
from app.main import app
from app.models.company import CompanyORM
from app.models.rbac import RoleORM
from app.models.tenant_registry import CompanyRegistryORM, SaasSubscriptionORM, SaasSuperAdminORM

client = TestClient(app)


def _register(tenant, email, password="StrongPassword123!", **extra):
    payload = {"tenant_id": tenant, "email": email, "password": password, "user_type": "admin"}
    payload.update(extra)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response


def test_new_company_gets_its_own_database_roles_and_subscription():
    suffix = uuid.uuid4().hex[:8]
    tenant = f"alpha-{suffix}"
    email = f"owner-{suffix}@example.com"
    _register(
        tenant,
        email,
        company_name="Société Alpha",
        legal_form="SARL",
        plan="trial",
    )

    central = CentralSessionLocal()
    try:
        company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant).one()
        subscription = central.query(SaasSubscriptionORM).filter_by(tenant_id=tenant).one()
        assert company.company_name == "Société Alpha"
        assert company.status == "active"
        assert company.database_name == f"nexa_tenant_alpha_{suffix}"
        assert company.logical_database_name.startswith(f"societe_alpha_{suffix}_")
        assert company.environment_code
        assert subscription.plan == "trial"
        assert subscription.status == "trialing"
    finally:
        central.close()

    db = get_tenant_sessionmaker(tenant)()
    try:
        names = {role.name for role in db.query(RoleORM).filter_by(tenant_id=tenant).all()}
        assert "Administrateur d'entreprise" in names
        assert "Responsable Commercial" in names
        assert "Ressources Humaines" in names
        assert "Production" in names
        profile = db.query(CompanyORM).filter_by(tenant_id=tenant).one()
        assert profile.name == "Société Alpha"
        assert profile.legal_form == "SARL"
    finally:
        db.close()

    login = client.post("/auth/login", data={"username": email, "password": "StrongPassword123!"})
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["workspace"] == "entreprise"
    assert body["tenant_id"] == tenant
    assert body["database_name"].startswith("nexa_tenant_alpha_")
    assert body["company_name"] == "Société Alpha"


def test_business_data_stays_inside_the_company_database():
    suffix = uuid.uuid4().hex[:8]
    left = f"left-{suffix}"
    right = f"right-{suffix}"
    password = "StrongPassword123!"
    _register(left, f"left-{suffix}@example.com")
    _register(right, f"right-{suffix}@example.com")
    left_token = client.post("/auth/login", data={"username": f"left-{suffix}@example.com", "password": password}).json()["access_token"]
    right_token = client.post("/auth/login", data={"username": f"right-{suffix}@example.com", "password": password}).json()["access_token"]

    created = client.post(
        "/products/",
        json={"name": "Pièce Alpha", "price": 12.5, "stock": 3},
        headers={"Authorization": f"Bearer {left_token}"},
    )
    assert created.status_code == 201, created.text

    right_products = client.get("/products/", headers={"Authorization": f"Bearer {right_token}"})
    assert right_products.status_code == 200
    assert right_products.json() == []
    left_products = client.get("/products/", headers={"Authorization": f"Bearer {left_token}"})
    assert [item["name"] for item in left_products.json()] == ["Pièce Alpha"]


def test_first_account_must_be_company_admin_and_super_admin_is_not_a_tenant_user():
    suffix = uuid.uuid4().hex[:8]
    staff = client.post("/auth/register", json={
        "tenant_id": f"staff-{suffix}",
        "email": f"staff-{suffix}@example.com",
        "password": "StrongPassword123!",
        "user_type": "staff",
    })
    assert staff.status_code == 422

    platform = client.post("/auth/register", json={
        "tenant_id": f"root-{suffix}",
        "email": f"root-{suffix}@example.com",
        "password": "StrongPassword123!",
        "user_type": "super_admin",
    })
    assert platform.status_code == 403


def test_company_admin_user_is_routed_by_the_central_registry():
    suffix = uuid.uuid4().hex[:8]
    tenant = f"team-{suffix}"
    password = "StrongPassword123!"
    _register(tenant, f"owner-{suffix}@example.com")
    token = client.post("/auth/login", data={"username": f"owner-{suffix}@example.com", "password": password}).json()["access_token"]
    created = client.post(
        "/users/",
        json={"email": f"sales-{suffix}@example.com", "password": password, "role": "commercial", "full_name": "Sara Sales"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["role_name"] == "Responsable Commercial"

    sales_login = client.post("/auth/login", data={"username": f"sales-{suffix}@example.com", "password": password})
    assert sales_login.status_code == 200, sales_login.text
    assert sales_login.json()["tenant_id"] == tenant
    whoami = client.get("/whoami", headers={"Authorization": f"Bearer {sales_login.json()['access_token']}"})
    assert whoami.json()["tenant_id"] == tenant
    assert whoami.json()["workspace"] == "entreprise"


def test_super_admin_sees_the_platform_and_needs_a_grant_to_enter_a_company():
    suffix = uuid.uuid4().hex[:8]
    tenant = f"grant-{suffix}"
    password = "StrongPassword123!"
    _register(tenant, f"owner-{suffix}@example.com", company_name="Société Grant")
    owner = client.post("/auth/login", data={"username": f"owner-{suffix}@example.com", "password": password}).json()["access_token"]
    client.post("/products/", json={"name": "Secret Grant", "price": 9, "stock": 1}, headers={"Authorization": f"Bearer {owner}"})

    central = CentralSessionLocal()
    try:
        central.query(SaasSuperAdminORM).filter(SaasSuperAdminORM.email.like("%@example.com")).delete(synchronize_session=False)
        central.commit()
    finally:
        central.close()

    bootstrap = client.post("/saas/bootstrap", json={"email": f"root-{suffix}@example.com", "password": password, "full_name": "Super Admin"})
    assert bootstrap.status_code == 201, bootstrap.text
    again = client.post("/saas/bootstrap", json={"email": f"other-{suffix}@example.com", "password": password})
    assert again.status_code == 409

    platform = client.post("/saas/login", json={"email": f"root-{suffix}@example.com", "password": password})
    assert platform.status_code == 200, platform.text
    platform_headers = {"Authorization": f"Bearer {platform.json()['access_token']}"}
    assert platform.json()["workspace"] == "plateforme"

    blocked = client.get("/products/", headers=platform_headers)
    assert blocked.status_code == 401

    overview = client.get("/saas/overview", headers=platform_headers)
    assert overview.status_code == 200, overview.text
    assert "products" not in overview.json()
    assert overview.json()["companies_active"] >= 1

    companies = client.get("/saas/companies", headers=platform_headers).json()
    assert any(item["tenant_id"] == tenant and "Secret" not in str(item) for item in companies)

    denied = client.post(f"/saas/companies/{tenant}/enter", headers=platform_headers)
    assert denied.status_code == 403

    grant = client.post(
        f"/saas/companies/{tenant}/grants",
        json={"reason": "Support demandé par l'entreprise", "minutes": 15},
        headers=platform_headers,
    )
    assert grant.status_code == 201, grant.text
    entered = client.post(f"/saas/companies/{tenant}/enter", headers=platform_headers)
    assert entered.status_code == 200, entered.text
    assert entered.json()["workspace"] == "entreprise"
    assert entered.json()["tenant_id"] == tenant

    support_headers = {"Authorization": f"Bearer {entered.json()['access_token']}"}
    visible = client.get("/products/", headers=support_headers)
    assert visible.status_code == 200, visible.text
    assert [item["name"] for item in visible.json()] == ["Secret Grant"]
    still_platform = client.get("/saas/overview", headers=support_headers)
    assert still_platform.status_code == 403
