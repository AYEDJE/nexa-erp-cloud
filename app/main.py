from fastapi import FastAPI, Depends
from starlette.middleware.cors import CORSMiddleware

from app.api import warehouse, invoices, products, users, ai
from app.api.audit import router as audit_router
from app.api.security_admin import router as security_admin_router
from app.api.documents import router as documents_router
from app.api.ocr import router as ocr_router
from app.api.search import router as search_router
from app.api.backups import router as backups_router
from app.routers import auth

from app.core.database import Base, engine
from app.core.tenant import get_current_tenant_id
from app.core.rbac import RoleChecker
from app.core.middleware import SecurityHeadersMiddleware

# Importation de tous les modèles pour création automatique des tables
from app.models.user import UserORM
from app.models.product import ProductORM
from app.models.rbac import PermissionORM, RoleORM
from app.models.invoice import InvoiceItemORM, InvoiceORM
from app.models.warehouse import StockMovementORM, WarehouseORM
from app.models.security import UserSessionORM, UserDeviceORM, SecurityAlertORM
import app.models.audit

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NexaERP Cloud API",
    description="Backend SaaS Multi-Tenant sécurisé avec RBAC, 2FA/MFA, Gestion des Appareils, Documents Word, OCR et Assistant IA",
    version="2.5.0",
)

# Protection & Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routeurs
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

allow_admin_only = RoleChecker(["admin", "super_admin"])


@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "NexaERP Cloud API",
        "version": "2.5.0",
        "security": "MFA, Sessions & Device Protection Enabled"
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": __import__('datetime').datetime.utcnow().isoformat()}


@app.get("/whoami")
def whoami(tenant_id: str = Depends(get_current_tenant_id)):
    return {"message": f"Vous appartenez à l'entreprise : {tenant_id}"}


@app.get("/admin/dashboard", dependencies=[Depends(allow_admin_only)])
def admin_dashboard():
    return {"message": "Accès autorisé : Panneau d'administration NexaERP Cloud."}
