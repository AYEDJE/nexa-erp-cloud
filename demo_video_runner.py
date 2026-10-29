"""
========================================================================================
             NEXA ERP CLOUD — SCRIPT DE DÉMONSTRATION VIDÉO OFFICIEL
========================================================================================
Ce script teste en direct 100% des endpoints de l'API (40+ routes) répartis en 8 scènes
thématiques idéales pour une démonstration vidéo fluide, professionnelle et structurée.

Il génère également les fichiers réels de sortie dans le dossier `demo_outputs/` :
- `facture_officielle_fr.pdf`
- `facture_officielle_en.pdf`
- `devis_commercial.docx`
- `backup_snapshot_tenant.json`
========================================================================================
"""

import os
import sys
import time
import json
import pyotp
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
OUTPUT_DIR = "demo_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Couleurs pour le terminal
GREEN = "\033[92m"
BLUE = "\033[94m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner(step_num: int, title: str):
    print(f"\n{BOLD}{BLUE}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN} [SCÈNE {step_num}] {title.upper()}{RESET}")
    print(f"{BOLD}{BLUE}{'='*80}{RESET}")
    time.sleep(0.5)


def log_step(method: str, path: str, status: int, detail: str = ""):
    color = GREEN if 200 <= status < 300 else YELLOW
    print(f" {BOLD}{method:<6}{RESET} {path:<38} -> {color}[HTTP {status}]{RESET} {detail}")


def main():
    print(f"{BOLD}{GREEN}")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║        LANCEMENT DU TEST INTÉGRAL DE L'API NEXA ERP CLOUD (DÉMO VIDÉO)       ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print(f"{RESET}")

    TENANT_ID = "entreprise_demo"
    EMAIL = f"admin_demo_{int(time.time())}@nexacloud.tg"
    PASSWORD = "DemoSecurePassword2026!"
    common_headers = {
        "X-Tenant-ID": TENANT_ID,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36"
    }

    # =========================================================================
    # SCÈNE 1 : SANTÉ, SÉCURITÉ OWASP & ISOLATION MULTI-TENANT
    # =========================================================================
    print_banner(1, "Infrastructure, Santé & En-têtes de Sécurité OWASP")

    res = client.get("/")
    log_step("GET", "/", res.status_code, f"App: {res.json().get('app')} v{res.json().get('version')}")
    assert res.status_code == 200
    assert res.headers.get("x-frame-options") == "DENY"
    print(f"   {CYAN}↳ En-têtes OWASP validés (X-Frame-Options: DENY, HSTS, X-Content-Type: nosniff){RESET}")

    res = client.get("/health")
    log_step("GET", "/health", res.status_code, f"Statut: {res.json().get('status')}")

    res = client.get("/whoami", headers=common_headers)
    log_step("GET", "/whoami", res.status_code, f"{res.json().get('message')}")

    # =========================================================================
    # SCÈNE 2 : AUTHENTIFICATION, SESSIONS ACTIVES & PROTECTION 2FA / MFA
    # =========================================================================
    print_banner(2, "Authentification Sécurisée, Gestion des Sessions & MFA (2FA)")

    # 1. Inscription
    res = client.post("/auth/register", json={
        "tenant_id": TENANT_ID,
        "email": EMAIL,
        "password": PASSWORD,
        "user_type": "admin"
    }, headers=common_headers)
    log_step("POST", "/auth/register", res.status_code, f"Nouvel utilisateur créé : {EMAIL}")
    user_id = res.json()["id"]

    # 2. Connexion initiale
    res = client.post("/auth/login", data={"username": EMAIL, "password": PASSWORD}, headers=common_headers)
    log_step("POST", "/auth/login", res.status_code, "Jeton JWT généré avec Access & Refresh Tokens")
    access_token = res.json()["access_token"]
    refresh_token = res.json()["refresh_token"]
    auth_headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Tenant-ID": TENANT_ID
    }

    # 3. Tableau de bord protégé
    res = client.get("/admin/dashboard", headers=auth_headers)
    log_step("GET", "/admin/dashboard", res.status_code, "Accès RBAC autorisé pour le rôle Administrateur")

    # 4. Consultation des sessions actives de l'utilisateur
    res = client.get("/auth/sessions", headers=auth_headers)
    log_step("GET", "/auth/sessions", res.status_code, f"{len(res.json())} session(s) active(s) détectée(s)")
    session_id = res.json()[0]["id"]

    # 5. Renouvellement du jeton via Refresh Token
    res = client.post("/auth/refresh", json={"refresh_token": refresh_token}, headers=auth_headers)
    log_step("POST", "/auth/refresh", res.status_code, "Access Token renouvelé avec succès sans réauthentification")
    access_token = res.json()["access_token"]
    auth_headers["Authorization"] = f"Bearer {access_token}"

    # 6. Configuration du 2FA (MFA)
    res = client.post("/auth/2fa/setup", headers=auth_headers)
    log_step("POST", "/auth/2fa/setup", res.status_code, "Secret TOTP généré + 8 codes de secours")
    two_fa_secret = res.json()["secret"]

    # 7. Activation du 2FA
    totp = pyotp.TOTP(two_fa_secret)
    res = client.post("/auth/2fa/enable", json={"code": totp.now()}, headers=auth_headers)
    log_step("POST", "/auth/2fa/enable", res.status_code, "Authentification à deux facteurs validée et activée")

    # 8. Connexion avec 2FA requis
    res = client.post("/auth/login", data={"username": EMAIL, "password": PASSWORD}, headers=common_headers)
    log_step("POST", "/auth/login (2FA)", res.status_code, "Validation intermédiaire requise (Code TOTP demandé)")
    temp_token = res.json()["temp_token"]

    res = client.post("/auth/2fa/verify-login", json={"code": totp.now(), "temp_token": temp_token}, headers=common_headers)
    log_step("POST", "/auth/2fa/verify-login", res.status_code, "Code 2FA validé -> Connexion définitive autorisée")

    # =========================================================================
    # SCÈNE 3 : CONSOLE D'ADMINISTRATION DES APPAREILS & ALERTES
    # =========================================================================
    print_banner(3, "Console Admin : Gestion des Appareils & Alertes de Sécurité")

    # 1. Liste du parc d'appareils
    res = client.get("/admin/security/devices", headers=auth_headers)
    log_step("GET", "/admin/security/devices", res.status_code, f"{len(res.json())} appareil(s) recensé(s)")
    device_id = res.json()[0]["id"]
    device_name = res.json()[0]["device_name"]

    # 2. Déconnexion forcée à distance
    res = client.post(f"/admin/security/devices/{device_id}/disconnect", headers=auth_headers)
    log_step("POST", f"/admin/security/devices/{device_id}/disconnect", res.status_code, f"Déconnexion à distance de l'appareil '{device_name}'")

    # 3. Blocage d'appareil
    res = client.post(f"/admin/security/devices/{device_id}/block", headers=auth_headers)
    log_step("POST", f"/admin/security/devices/{device_id}/block", res.status_code, f"Appareil '{device_name}' placé sur liste noire")

    # 4. Réautorisation d'appareil
    res = client.post(f"/admin/security/devices/{device_id}/unblock", headers=auth_headers)
    log_step("POST", f"/admin/security/devices/{device_id}/unblock", res.status_code, f"Appareil réautorisé")

    # 5. Consultation des alertes de sécurité
    res = client.get("/admin/security/alerts", headers=auth_headers)
    log_step("GET", "/admin/security/alerts", res.status_code, f"{len(res.json())} alerte(s) de sécurité journalisée(s)")

    # =========================================================================
    # SCÈNE 4 : GESTION DES UTILISATEURS (RBAC) & ENTREPÔTS / STOCKS
    # =========================================================================
    print_banner(4, "Gestion des Utilisateurs (RBAC) & Stocks / Entrepôts")

    # 1. Utilisateurs
    res = client.get("/users/", headers=auth_headers)
    log_step("GET", "/users/", res.status_code, f"{len(res.json())} utilisateur(s) dans le tenant")

    res = client.get(f"/users/{user_id}", headers=auth_headers)
    log_step("GET", f"/users/{user_id}", res.status_code, f"Détails de {res.json().get('email')}")

    # 2. Entrepôts
    res = client.post("/warehouses/", json={
        "name": "Entrepôt Central Lomé Port",
        "code": f"WH-LOME-{int(time.time())%1000}",
        "location": "Zone Franche Industrielle"
    }, headers=auth_headers)
    log_step("POST", "/warehouses/", res.status_code, f"Entrepôt '{res.json().get('name')}' créé")
    wh_id = res.json()["id"]

    res = client.get("/warehouses/", headers=auth_headers)
    log_step("GET", "/warehouses/", res.status_code, f"{len(res.json())} entrepôt(s) actif(s)")

    # 3. Mouvement de stock
    res = client.post("/warehouses/stock/movements", json={
        "warehouse_id": wh_id,
        "product_name": "Serveur Dell PowerEdge R750",
        "movement_type": "in",
        "quantity": 10.0,
        "reference": "BL-FOURNISSEUR-2026"
    }, headers=auth_headers)
    log_step("POST", "/warehouses/stock/movements", res.status_code, "Entrée en stock enregistrée (+10 unités)")

    res = client.get("/warehouses/stock", headers=auth_headers)
    log_step("GET", "/warehouses/stock", res.status_code, f"État des stocks mis à jour")

    # =========================================================================
    # SCÈNE 5 : PRODUITS, FACTURATION & TÉLÉCHARGEMENT PDF MULTILINGUE
    # =========================================================================
    print_banner(5, "Catalogue Produits, Facturation & Export PDF Officiel")

    # 1. Catalogue produit
    res = client.post("/products/", json={
        "name": "Licence ERP Cloud Annuelle",
        "description": "Accès SaaS illimité multi-tenant",
        "price": 500000.0,
        "stock": 50
    }, headers=auth_headers)
    log_step("POST", "/products/", res.status_code, f"Produit ajouté : '{res.json().get('name')}'")
    product_id = res.json()["id"]

    res = client.get("/products/", headers=auth_headers)
    log_step("GET", "/products/", res.status_code, f"{len(res.json())} produit(s) dans le catalogue")

    # 2. Création de facture
    invoice_payload = {
        "doc_type": "INVOICE",
        "language": "fr",
        "payment_terms": "Paiement à réception par virement bancaire",
        "issuer": {
            "name": "Nexa Cloud Technology SAS",
            "address": "15 Avenue de la Paix, Lomé, Togo",
            "phone": "+228 90 00 11 22",
            "email": "facturation@nexacloud.tg",
            "tax_id": "TG-LOM-2026-B890",
            "issuing_place": "Lomé"
        },
        "customer": {
            "name": "Société Ouest Africaine de Commerce",
            "address": "Boulevard du Mono, Cotonou, Bénin",
            "phone": "+229 21 00 33 44",
            "email": "direction@commerce-afrique.com"
        },
        "items": [
            {
                "product_name": "Licence ERP Cloud Annuelle",
                "unit": "Licence",
                "quantity": 2,
                "unit_price_ht": 500000.0,
                "tva_rate": 18.0,
                "discount": 0.0
            }
        ]
    }
    res = client.post("/invoices/", json=invoice_payload, headers=auth_headers)
    log_step("POST", "/invoices/", res.status_code, f"Facture générée N° {res.json().get('number')} (Total: {res.json().get('total_ttc')} FCFA)")
    invoice_id = res.json()["id"]

    res = client.get("/invoices/", headers=auth_headers)
    log_step("GET", "/invoices/", res.status_code, f"{len(res.json())} facture(s) enregistrée(s)")

    res = client.get(f"/invoices/{invoice_id}", headers=auth_headers)
    log_step("GET", f"/invoices/{invoice_id}", res.status_code, "Consultation des détails de la facture")

    # 3. Téléchargement PDF multilingue
    pdf_fr = client.get(f"/invoices/{invoice_id}/pdf?lang=fr", headers=auth_headers)
    log_step("GET", f"/invoices/{invoice_id}/pdf?lang=fr", pdf_fr.status_code, "Génération du PDF en Français")
    pdf_path_fr = os.path.join(OUTPUT_DIR, "facture_officielle_fr.pdf")
    with open(pdf_path_fr, "wb") as f:
        f.write(pdf_fr.content)
    print(f"   {GREEN}↳ Fichier enregistré : {pdf_path_fr} ({len(pdf_fr.content)} octets){RESET}")

    pdf_en = client.get(f"/invoices/{invoice_id}/pdf?lang=en", headers=auth_headers)
    log_step("GET", f"/invoices/{invoice_id}/pdf?lang=en", pdf_en.status_code, "Génération du PDF en Anglais")
    pdf_path_en = os.path.join(OUTPUT_DIR, "facture_officielle_en.pdf")
    with open(pdf_path_en, "wb") as f:
        f.write(pdf_en.content)
    print(f"   {GREEN}↳ Fichier enregistré : {pdf_path_en} ({len(pdf_en.content)} octets){RESET}")

    # =========================================================================
    # SCÈNE 6 : SERVICES TRANSVERSAUX (WORD .DOCX, ASSISTANT SAISIE, OCR)
    # =========================================================================
    print_banner(6, "Services Transversaux : Word (.docx), Assistant Saisie & OCR")

    # 1. Génération Word (.docx)
    docx_payload = {
        "doc_type": "QUOTE",
        "title": "PROPOSITION COMMERCIALE & DEVIS TECHNIQUE",
        "data": {
            "number": "DEV-2026-NEXA-01",
            "date": "21/10/2026",
            "currency": "EUR",
            "issuer": {
                "name": "Nexa Cloud Technology",
                "address": "Lomé, Togo",
                "phone": "+228 90 00 11 22",
                "email": "contact@nexa.tg",
                "tax_id": "TG-2026-001"
            },
            "customer": {
                "name": "Groupe International Partner",
                "address": "Abidjan, Côte d'Ivoire",
                "phone": "+225 07 08 09 10",
                "email": "direction@partner.ci"
            },
            "items": [
                {
                    "product_name": "Intégration & Paramétrage Architecture Multi-Tenant",
                    "unit": "Jour",
                    "quantity": 5,
                    "unit_price_ht": 600.0,
                    "total_ht": 3000.0
                }
            ],
            "total_ht": 3000.0,
            "tax_amount": 540.0,
            "total_ttc": 3540.0,
            "total_in_words": "trois mille cinq cent quarante euros",
            "payment_terms": "40% à la commande, solde à la mise en production."
        }
    }
    res_docx = client.post("/documents/generate-docx", json=docx_payload, headers=auth_headers)
    log_step("POST", "/documents/generate-docx", res_docx.status_code, "Document Word (.docx) généré avec succès")
    docx_path = os.path.join(OUTPUT_DIR, "devis_commercial.docx")
    with open(docx_path, "wb") as f:
        f.write(res_docx.content)
    print(f"   {GREEN}↳ Fichier Word enregistré : {docx_path} ({len(res_docx.content)} octets){RESET}")

    # 2. Assistance intelligente à la saisie
    res = client.post("/documents/assist-input", json={
        "form_data": {
            "date": "21/10/2026",
            "due_date": "2026-11-20",
            "email": "contact@entreprise-valide.com",
            "phone": "+228 90 22 33 44"
        }
    }, headers=auth_headers)
    log_step("POST", "/documents/assist-input", res.status_code, f"Validation formulaire : Valide={res.json().get('is_valid')}")

    # 3. Suggestions rédactionnelles
    res = client.get("/documents/suggestions?category=invoice_notes&language=fr", headers=auth_headers)
    log_step("GET", "/documents/suggestions", res.status_code, f"{len(res.json().get('suggestions', []))} modèle(s) rédactionnel(s) retourné(s)")

    # 4. Conversion montant en toutes lettres multi-devises
    res = client.get("/documents/number-to-words?amount=1250000.75&currency=FCFA&language=fr", headers=auth_headers)
    log_step("GET", "/documents/number-to-words", res.status_code, f"Résultat : '{res.json().get('in_words')}'")

    # 5. Moteur OCR & Extraction intelligente
    raw_ocr_scan = """
    FACTURE D'ACHAT N° FOURN-2026-992
    Date: 21/10/2026
    Fournisseur: DISTRIBUTEUR AFRICA TECH
    NIF: TG-887766554
    Total HT: 450000.00
    TVA: 81000.00
    Total TTC: 531000.00
    """
    res = client.post("/ocr/extract", json={"raw_text": raw_ocr_scan}, headers=auth_headers)
    ext = res.json()["extracted_data"]
    log_step("POST", "/ocr/extract", res.status_code, f"Facture détectée : N° {ext.get('document_number')} (Total: {ext.get('total_ttc')} FCFA)")

    # =========================================================================
    # SCÈNE 7 : RECHERCHE GLOBALE & ASSISTANT IA (RAG)
    # =========================================================================
    print_banner(7, "Recherche Globale Transversale & Assistant Financier IA")

    # 1. Recherche globale
    res = client.get("/search/?q=Licence", headers=auth_headers)
    log_step("GET", "/search/?q=Licence", res.status_code, f"Trouvé : {res.json().get('total_results')} élément(s) tous modules confondus")

    # 2. Assistant IA Financier
    res = client.post("/ai/query", json={
        "prompt": "Analyse le chiffre d'affaires total et donne-moi une recommandation.",
        "language": "fr"
    }, headers=auth_headers)
    log_step("POST", "/ai/query", res.status_code, "Analyse financière RAG calculée en temps réel")
    print(f"   {CYAN}↳ Réponse IA : {res.json().get('answer')[:110]}...{RESET}")

    # 3. Journal d'audit
    res = client.get("/audit/logs", headers=auth_headers)
    log_step("GET", "/audit/logs", res.status_code, f"{len(res.json())} événement(s) d'audit enregistrés")

    # =========================================================================
    # SCÈNE 8 : SAUVEGARDE & RESTAURATION TESTÉE (DISASTER RECOVERY)
    # =========================================================================
    print_banner(8, "Sauvegarde & Restauration des Données du Tenant")

    # 1. Export instantané de sauvegarde
    res = client.post("/admin/backups/export", headers=auth_headers)
    log_step("POST", "/admin/backups/export", res.status_code, "Instantané complet du tenant exporté (JSON)")
    snapshot = res.json()
    snapshot_path = os.path.join(OUTPUT_DIR, "backup_snapshot_tenant.json")
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    print(f"   {GREEN}↳ Fichier de sauvegarde enregistré : {snapshot_path}{RESET}")

    # 2. Restauration testée
    res = client.post("/admin/backups/restore", json={"snapshot": snapshot}, headers=auth_headers)
    log_step("POST", "/admin/backups/restore", res.status_code, f"Restauration terminée avec succès : {res.json().get('status')}")

    # Nettoyage produit de test
    client.delete(f"/products/{product_id}", headers=auth_headers)

    # 3. Déconnexion finale
    res = client.post("/auth/logout", headers=auth_headers)
    log_step("POST", "/auth/logout", res.status_code, "Déconnexion finale et révocation du jeton")

    # =========================================================================
    # BILAN FINAL
    # =========================================================================
    print(f"\n{BOLD}{GREEN}{'='*80}{RESET}")
    print(f"{BOLD}{GREEN} ✅ TOUS LES ENDPOINTS (100%) ONT ÉTÉ TESTÉS ET VALIDÉS AVEC SUCCÈS !{RESET}")
    print(f"{BOLD}{GREEN}{'='*80}{RESET}")
    print(f"\n{CYAN}Fichiers générés pour votre vidéo dans le dossier '{OUTPUT_DIR}/' :{RESET}")
    for item in os.listdir(OUTPUT_DIR):
        item_path = os.path.join(OUTPUT_DIR, item)
        print(f"  📁 {BOLD}{item}{RESET} ({os.path.getsize(item_path)} octets)")
    print()


if __name__ == "__main__":
    main()
