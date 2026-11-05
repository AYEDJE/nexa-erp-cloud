from fastapi import APIRouter, Depends, FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api import warehouse, invoices, products, users, ai
from app.api.audit import router as audit_router
from app.api.security_admin import router as security_admin_router
from app.api.documents import router as documents_router
from app.api.ocr import router as ocr_router
from app.api.search import router as search_router
from app.api.backups import router as backups_router
from app.api.company import router as company_router
from app.routers import auth
from app.core.database import CentralBase, central_engine
from app.core.rbac import RoleChecker
from app.core.middleware import SecurityHeadersMiddleware
from app.models.tenant_registry import CompanyRegistryORM, TenantUserRegistryORM
from app.routers import saas_auth

# Import all ERP models so their metadata is available to tenant provisioning.
from app.models.user import UserORM
from app.models.product import ProductORM
from app.models.rbac import PermissionORM, RoleORM
from app.models.invoice import InvoiceItemORM, InvoiceORM
from app.models.warehouse import StockMovementORM, WarehouseORM
from app.models.security import UserSessionORM, UserDeviceORM, SecurityAlertORM
from app.models.company import CompanyORM
import app.models.audit

CentralBase.metadata.create_all(bind=central_engine)

app = FastAPI(
    title="NexaERP Cloud API",
    description="Backend SaaS Multi-Tenant avec registre central et bases ERP isolées par entreprise",
    version="2.6.0",
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register central SaaS auth endpoints before legacy endpoints with the same paths.
app.include_router(saas_auth.router)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(invoices.router)
app.include_router(warehouse.router)
app.include_router(documents_router)
app.include_router(ocr_router)
app.include_router(search_router)
app.include_router(ai.router)
app.include_router(audit_router)
app.include_router(security_admin_router)
app.include_router(backups_router)
app.include_router(company_router)

allow_admin_only = RoleChecker(["admin", "super_admin"])


@app.get("/")
def read_root():
    return {"status": "online", "app": "NexaERP Cloud API", "version": "2.6.0", "security": "Central registry and tenant-isolated databases"}


@app.get("/health")
def health_check():
    from datetime import datetime
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/whoami")
def whoami(tenant_id: str = Depends(__import__("app.core.tenant", fromlist=["get_current_tenant_id"]).get_current_tenant_id)):
    return {"message": f"Vous appartenez à l'entreprise : {tenant_id}"}


@app.get("/admin/dashboard", dependencies=[Depends(allow_admin_only)])
def admin_dashboard():
    return {"message": "Accès autorisé : Panneau d'administration NexaERP Cloud."}
