import pytest
import pyotp
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_and_security_headers():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"
    # Vérification des headers de sécurité OWASP
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_whoami():
    response = client.get("/whoami", headers={"X-Tenant-ID": "test_tenant"})
    assert response.status_code == 200
    assert "test_tenant" in response.json()["message"]


def test_complete_auth_session_device_and_mfa_flow():
    tenant_id = "tenant_security"
    common_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "X-Tenant-ID": tenant_id
    }
    email = f"user_sec_{__import__('uuid').uuid4().hex[:6]}@example.com"
    pwd = "StrongPassword123!"

    # 1. Inscription
    reg_res = client.post("/auth/register", json={
        "tenant_id": tenant_id,
        "email": email,
        "password": pwd,
        "user_type": "admin"
    }, headers=common_headers)
    assert reg_res.status_code == 201

    # 2. Première connexion -> vérification de session et appareil
    login_res = client.post(
        "/auth/login",
        data={"username": email, "password": pwd},
        headers=common_headers
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["requires_2fa"] is False
    assert "access_token" in login_data
    assert "refresh_token" in login_data

    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]
    auth_headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Tenant-ID": tenant_id
    }

    # 3. Vérification des sessions actives
    sessions_res = client.get("/auth/sessions", headers=auth_headers)
    assert sessions_res.status_code == 200
    sessions = sessions_res.json()
    assert len(sessions) >= 1
    assert sessions[0]["is_revoked"] is False

    # 4. Renouvellement de session via Refresh Token
    refresh_res = client.post("/auth/refresh", json={"refresh_token": refresh_token}, headers=auth_headers)
    assert refresh_res.status_code == 200
    new_access_token = refresh_res.json()["access_token"]
    assert new_access_token != access_token
    auth_headers["Authorization"] = f"Bearer {new_access_token}"

    # 5. Configuration et activation du 2FA (MFA)
    setup_2fa_res = client.post("/auth/2fa/setup", headers=auth_headers)
    assert setup_2fa_res.status_code == 200
    setup_data = setup_2fa_res.json()
    secret = setup_data["secret"]
    assert len(setup_data["backup_codes"]) == 8

    # Génération du code TOTP valide
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    enable_res = client.post("/auth/2fa/enable", json={"code": valid_code}, headers=auth_headers)
    assert enable_res.status_code == 200

    # 6. Connexion avec 2FA activé -> doit demander le code 2FA
    login_2fa_req = client.post(
        "/auth/login",
        data={"username": email, "password": pwd},
        headers=common_headers
    )
    assert login_2fa_req.status_code == 200
    login_2fa_data = login_2fa_req.json()
    assert login_2fa_data["requires_2fa"] is True
    temp_token = login_2fa_data["temp_token"]

    # Validation du code 2FA
    verify_2fa_res = client.post(
        "/auth/2fa/verify-login",
        json={"code": totp.now(), "temp_token": temp_token},
        headers=common_headers
    )
    assert verify_2fa_res.status_code == 200
    assert "access_token" in verify_2fa_res.json()

    # 7. Déconnexion (Logout) et vérification de la révocation
    logout_res = client.post("/auth/logout", headers=auth_headers)
    assert logout_res.status_code == 200


def test_device_management_and_security_alerts():
    tenant_id = "tenant_devices"
    headers = {
        "User-Agent": "Mozilla/5.0 Firefox/115.0",
        "X-Tenant-ID": tenant_id
    }
    email = f"admin_dev_{__import__('uuid').uuid4().hex[:6]}@example.com"
    pwd = "DevPassword123!"

    client.post("/auth/register", json={
        "tenant_id": tenant_id, "email": email, "password": pwd, "user_type": "admin"
    }, headers=headers)

    login_res = client.post(
        "/auth/login",
        data={"username": email, "password": pwd},
        headers=headers
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

    # Liste des appareils
    devices_res = client.get("/admin/security/devices", headers=auth_headers)
    assert devices_res.status_code == 200
    devices = devices_res.json()
    assert len(devices) >= 1
    dev_id = devices[0]["id"]

    # Déconnexion à distance
    disc_res = client.post(f"/admin/security/devices/{dev_id}/disconnect", headers=auth_headers)
    assert disc_res.status_code == 200

    # Blocage d'appareil
    block_res = client.post(f"/admin/security/devices/{dev_id}/block", headers=auth_headers)
    assert block_res.status_code == 200

    # Déblocage d'appareil
    unblock_res = client.post(f"/admin/security/devices/{dev_id}/unblock", headers=auth_headers)
    assert unblock_res.status_code == 200

    # Liste des alertes de sécurité
    alerts_res = client.get("/admin/security/alerts", headers=auth_headers)
    assert alerts_res.status_code == 200


def test_products_and_invoices_flow():
    tenant_id = "tenant_erp"
    headers = {"X-Tenant-ID": tenant_id}
    email = f"staff_{__import__('uuid').uuid4().hex[:6]}@example.com"
    pwd = "StaffPassword123!"

    client.post("/auth/register", json={
        "tenant_id": tenant_id, "email": email, "password": pwd, "user_type": "admin"
    }, headers=headers)
    token = client.post("/auth/login", data={"username": email, "password": pwd}, headers=headers).json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

    # 1. Produit
    prod_res = client.post("/products/", json={
        "name": "Serveur Dédié", "description": "Cloud hosting", "price": 85000.0, "stock": 5
    }, headers=auth_headers)
    assert prod_res.status_code == 201

    # 2. Facture
    inv_res = client.post("/invoices/", json={
        "doc_type": "INVOICE",
        "language": "fr",
        "payment_terms": "Paiement à 30 jours",
        "issuer": {
            "name": "Nexa Systems", "address": "Lomé, Togo", "phone": "+22890000000",
            "email": "contact@nexa.tg", "tax_id": "TG-8899", "issuing_place": "Lomé"
        },
        "customer": {
            "name": "Client Entreprise", "address": "Abidjan, CI", "phone": "+22501020304", "email": "client@ci.com"
        },
        "items": [
            {"product_name": "Serveur Dédié", "unit": "Mois", "quantity": 1, "unit_price_ht": 85000.0, "tva_rate": 18.0, "discount": 0.0}
        ]
    }, headers=auth_headers)
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["id"]

    # PDF de la facture
    pdf_res = client.get(f"/invoices/{inv_id}/pdf", headers=auth_headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"


def test_transversal_docx_document_generation():
    headers = {"X-Tenant-ID": "tenant_docs"}
    payload = {
        "doc_type": "QUOTE",
        "title": "DEVIS COMMERCIAL — PRESTATION CLOUD",
        "data": {
            "number": "DEV-2026-001",
            "date": "21/10/2026",
            "currency": "EUR",
            "issuer": {
                "name": "Nexa Cloud Corp",
                "address": "Paris, France",
                "phone": "+33140000000",
                "email": "sales@nexa.eu",
                "tax_id": "FR12345678"
            },
            "customer": {
                "name": "Global Logistics SAS",
                "address": "Lyon, France",
                "phone": "+33470000000",
                "email": "contact@globallogistics.fr"
            },
            "items": [
                {"product_name": "Déploiement Architecture SaaS", "unit": "Jour", "quantity": 5, "unit_price_ht": 800.0, "total_ht": 4000.0}
            ],
            "total_ht": 4000.0,
            "tax_amount": 800.0,
            "total_ttc": 4800.0,
            "total_in_words": "quatre mille huit cents euros",
            "payment_terms": "30% à la commande, solde à la livraison."
        }
    }
    res = client.post("/documents/generate-docx", json=payload, headers=headers)
    assert res.status_code == 200
    assert "wordprocessingml.document" in res.headers["content-type"]
    assert len(res.content) > 1000


def test_smart_text_assistance_and_multi_currency():
    headers = {"X-Tenant-ID": "tenant_docs"}

    # 1. Validation intelligente de formulaire
    form_res = client.post("/documents/assist-input", json={
        "form_data": {
            "date": "21/10/2026",
            "due_date": "2026-11-20",
            "email": "bon.format@entreprise.com",
            "phone": "+228 90 11 22 33"
        }
    }, headers=headers)
    assert form_res.status_code == 200
    assert form_res.json()["is_valid"] is True

    # 2. Suggestions rédactionnelles
    sugg_res = client.get("/documents/suggestions?category=invoice_notes&language=fr", headers=headers)
    assert sugg_res.status_code == 200
    assert len(sugg_res.json()["suggestions"]) >= 2

    # 3. Montant en lettres multi-devises (EUR, FCFA, USD, MAD)
    curr_res = client.get("/documents/number-to-words?amount=1500.50&currency=EUR&language=fr", headers=headers)
    assert curr_res.status_code == 200
    assert "euros" in curr_res.json()["in_words"]


def test_smart_ocr_and_data_extraction():
    headers = {"X-Tenant-ID": "tenant_ocr"}
    raw_sample = """
    FACTURE N° FAC-2026-789
    Date: 21/10/2026
    Fournisseur: TECHNOLOGIES SARL
    NIF: TG-987654321
    Description: Support Maintenance Informatique
    Total HT: 250000.00
    Total TVA: 45000.00
    Total TTC: 295000.00
    """
    ocr_res = client.post("/ocr/extract", json={"raw_text": raw_sample}, headers=headers)
    assert ocr_res.status_code == 200
    data = ocr_res.json()["extracted_data"]
    assert data["document_number"] == "FAC-2026-789"
    assert data["total_ttc"] == 295000.0
    assert data["total_ht"] == 250000.0
    assert data["tax_amount"] == 45000.0
    assert data["date"] == "2026-10-21"


def test_global_cross_module_search():
    tenant_id = "tenant_search"
    headers = {"X-Tenant-ID": tenant_id}
    email = f"search_admin_{__import__('uuid').uuid4().hex[:6]}@example.com"
    pwd = "SearchPassword123!"

    client.post("/auth/register", json={
        "tenant_id": tenant_id, "email": email, "password": pwd, "user_type": "admin"
    }, headers=headers)
    token = client.post("/auth/login", data={"username": email, "password": pwd}, headers=headers).json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

    # Création d'un produit identifiable
    client.post("/products/", json={
        "name": "Imprimante Laser Pro", "price": 120000.0, "stock": 3
    }, headers=auth_headers)

    # Recherche
    search_res = client.get("/search/?q=Imprimante", headers=auth_headers)
    assert search_res.status_code == 200
    results = search_res.json()
    assert results["total_results"] >= 1
    assert any(p["name"] == "Imprimante Laser Pro" for p in results["results"]["products"])


def test_tenant_backup_export_and_restore():
    tenant_id = "tenant_backup_test"
    headers = {"X-Tenant-ID": tenant_id}
    email = f"backup_admin_{__import__('uuid').uuid4().hex[:6]}@example.com"
    pwd = "BackupPassword123!"

    client.post("/auth/register", json={
        "tenant_id": tenant_id, "email": email, "password": pwd, "user_type": "admin"
    }, headers=headers)
    token = client.post("/auth/login", data={"username": email, "password": pwd}, headers=headers).json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

    # 1. Export backup snapshot
    export_res = client.post("/admin/backups/export", headers=auth_headers)
    assert export_res.status_code == 200
    snapshot = export_res.json()
    assert snapshot["metadata"]["tenant_id"] == tenant_id

    # 2. Restore snapshot
    restore_res = client.post("/admin/backups/restore", json={"snapshot": snapshot}, headers=auth_headers)
    assert restore_res.status_code == 200
    assert restore_res.json()["status"] == "success"
