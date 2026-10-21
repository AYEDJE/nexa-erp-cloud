# Rapport de Correction — Nexa ERP Cloud

Ce document récapitule l'ensemble des anomalies corrigées dans le projet **Nexa ERP Cloud**.

---

## 📋 Fichiers modifiés et créés

| Fichier | Statut | Rôle de la modification |
| :--- | :---: | :--- |
| `app/main.py` | Modifié | Réorganisation des imports, ordre d'instanciation de `FastAPI`, import de `Depends` et inclusion du routeur `auth`. |
| `app/core/security.py` | Modifié | Remplacement de `passlib` par `bcrypt` direct (contournement du bug Python / bcrypt 4+). |
| `app/core/database.py` | Modifié | `X-Tenant-ID` rendu optionnel avec repli sur `SessionLocal` par défaut (compatibilité `/docs` et OAuth2). |
| `app/core/tenant_db.py` | Modifié | `check_same_thread=False` et auto-initialisation du schéma SQLAlchemy pour chaque nouveau tenant. |
| `app/core/rbac.py` | Modifié | Vérification de la présence du token avant décodage JWT (évite un code HTTP 500). |
| `app/services/tenant_provisioning.py` | Modifié | Correction des imports inexistants, typos de variables et syntaxe SQL. |
| `app/services/seed_rbac.py` | Modifié | Alignement sur les colonnes réelles de `RoleORM` et `PermissionORM`. |
| `app/utils/number_to_words.py` | Modifié | Fallback sécurisé en cas d'absence de `num2words`. |
| `requirements.txt` | Créé | Dépendances nécessaires (`fastapi`, `uvicorn`, `bcrypt`, `python-multipart`, `num2words`, etc.). |
| `pytest.ini` | Créé | Définition du `pythonpath` pour l'exécution des tests. |
| `.gitignore` | Créé | Exclusion des fichiers temporaires, caches et bases SQLite locales. |
| `tests/test_api.py` | Créé | 8 tests d'intégration complets validés avec succès. |

---

## 🧪 Exécution des tests et lancement

### Lancer la suite de tests
```powershell
.\venv\Scripts\python.exe -m pytest -v
```
*(Résultat : 8/8 tests passés avec succès)*

### Démarrer le serveur API
```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```
Documentation Swagger accessible sur : http://127.0.0.1:8000/docs
