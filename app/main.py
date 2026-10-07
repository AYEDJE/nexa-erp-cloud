from app.api import warehouse
from app.api import invoices, products, users, ai
from app.core.database import Base, engine
from app.core.tenant import get_current_tenant_id
from app.core.rbac import RoleChecker
from app.models.user import UserORM
from app.models.product import ProductORM
from app.models.rbac import PermissionORM, RoleORM
from app.models.invoice import InvoiceItemORM, InvoiceORM
from app.models.warehouse import StockMovementORM, WarehouseORM
import app.models.audit
from app.api.audit import router as audit_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NexaERP Cloud API",
    description="Backend SaaS Multi-Tenant sécurisé avec RBAC, Facturation et Assistant IA",
    version="2.0.0",
)

from fastapi import FastAPI

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(invoices.router)
app.include_router(ai.router)
app.include_router(audit_router)
app.include_router(warehouse.router)

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
