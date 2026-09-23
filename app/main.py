from fastapi import FastAPI, Depends
from app.core.database import Base, engine
from app.core.tenant import get_current_tenant
from app.core.rbac import RoleChecker

# Modèles BDD
from app.models.user import UserORM
from app.models.product import ProductORM
from app.models.rbac import RoleORM, PermissionORM

# Routeurs API
from app.api import products, users
from app.routers import auth

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NexaERP Cloud API",
    description="Backend SaaS Multi-Tenant sécurisé avec RBAC",
    version="1.0.0"
)

# Inclusion des modules
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(users.router)

allow_admin_only = RoleChecker(["admin", "super_admin"])


@app.get("/")
def read_root():
    return {"status": "online", "message": "NexaERP Cloud API est opérationnel"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/whoami")
def whoami(tenant_id: str = Depends(get_current_tenant)):
    return {"message": f"Vous appartenez à l'entreprise : {tenant_id}"}


@app.get("/admin/dashboard", dependencies=[Depends(allow_admin_only)])
def admin_dashboard():
    return {"message": "Accès autorisé : Panneau d'administration NexaERP Cloud."}