from fastapi import FastAPI, Depends
from app.core.database import Base, engine
from app.core.tenant import get_current_tenant_id
from app.core.rbac import RoleChecker

# 1. Modèles BDD (Pour s'assurer que SQLAlchemy crée toutes les tables)
from app.models.user import UserORM
from app.models.product import ProductORM
from app.models.rbac import RoleORM, PermissionORM
from app.models.invoice import InvoiceORM, InvoiceItemORM  # <-- Inclus les factures
import app.models.audit
from app.api.audit import router as audit_router
# 2. Création automatique des tables
Base.metadata.create_all(bind=engine)

# 3. Instanciation de l'application FastAPI
app = FastAPI(
    title="NexaERP Cloud API",
    description="Backend SaaS Multi-Tenant sécurisé avec RBAC, Facturation et Assistant IA",
    version="2.0.0"
)

# 4. Importation et inclusion de TOUS les routeurs API (Inclusion de `ai`)
from app.api import invoices, products, users, ai  # <-- Ajout du module ai ici
from app.routers import auth

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(invoices.router)
app.include_router(ai.router)  # <-- Routeur de l'Assistant IA 
app.include_router(audit_router) # <-- Routeur d'audit
# 5. Contrôle d'accès RBAC
allow_admin_only = RoleChecker(["admin", "super_admin"])


@app.get("/")
def read_root():
    return {"status": "online", "message": "NexaERP Cloud API est opérationnel"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/whoami")
def whoami(tenant_id: str = Depends(get_current_tenant_id)):
    return {"message": f"Vous appartenez à l'entreprise : {tenant_id}"}


@app.get("/admin/dashboard", dependencies=[Depends(allow_admin_only)])
def admin_dashboard():
    return {"message": "Accès autorisé : Panneau d'administration NexaERP Cloud."}