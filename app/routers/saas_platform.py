from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.database import get_central_db
from app.core.security import create_access_token, get_password_hash, normalize_email, verify_password
from app.core.tenant_db import normalize_tenant_id
from app.models.tenant_registry import (
    CompanyRegistryORM,
    SaasAccessGrantORM,
    SaasAuditLogORM,
    SaasLoginEventORM,
    SaasSubscriptionORM,
    SaasSuperAdminORM,
)
from app.services.saas_platform_service import record_audit, record_login_event

router = APIRouter(prefix="/saas", tags=["Plateforme SaaS"])


class SuperAdminCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class SuperAdminLogin(BaseModel):
    email: EmailStr
    password: str


class AccessGrantIn(BaseModel):
    reason: str = Field(min_length=5, max_length=300)
    minutes: int = Field(default=30, ge=5, le=120)


def get_platform_admin(
    authorization: str = Header(default=""),
    central: Session = Depends(get_central_db),
) -> SaasSuperAdminORM:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton plateforme requis.")
    token = authorization.split(None, 1)[1]
    from jose import JWTError, jwt
    from app.core.config import ALGORITHM, SECRET_KEY

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton invalide ou expiré.") from exc
    if payload.get("actor") != "super_admin" or payload.get("tenant_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cet espace est réservé au super administrateur de la plateforme.")
    admin = central.query(SaasSuperAdminORM).filter_by(email=normalize_email(payload.get("sub") or ""), is_active=True).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Super administrateur introuvable ou inactif.")
    return admin


def _company_view(company: CompanyRegistryORM, subscription: SaasSubscriptionORM | None) -> dict:
    return {
        "tenant_id": company.tenant_id,
        "company_name": company.company_name,
        "status": company.status,
        "locale": company.locale,
        "database_name": company.database_name,
        "logical_database_name": company.logical_database_name,
        "environment_code": company.environment_code,
        "plan": subscription.plan if subscription else None,
        "subscription_status": subscription.status if subscription else None,
        "licensed_users": subscription.licensed_users if subscription else None,
        "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription and subscription.trial_ends_at else None,
        "created_at": company.created_at.isoformat() if company.created_at else None,
    }


@router.post("/bootstrap", status_code=status.HTTP_201_CREATED)
def bootstrap_super_admin(
    body: SuperAdminCreate,
    central: Session = Depends(get_central_db),
    x_setup_key: str | None = Header(default=None, alias="X-Setup-Key"),
):
    """Crée le premier super administrateur. Refusé dès qu'un compte plateforme existe."""
    import os

    expected = os.getenv("NEXA_SETUP_KEY")
    if expected and x_setup_key != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clé de mise en service invalide.")
    if central.query(SaasSuperAdminORM).count():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un super administrateur existe déjà.")
    admin = SaasSuperAdminORM(
        email=normalize_email(str(body.email)),
        full_name=(body.full_name or "").strip() or None,
        hashed_password=get_password_hash(body.password),
        is_active=True,
    )
    central.add(admin)
    central.commit()
    record_audit("system", "super_admin_bootstrapped", actor_email=admin.email)
    return {"email": admin.email, "workspace": "plateforme"}


@router.post("/login")
def login_super_admin(body: SuperAdminLogin, central: Session = Depends(get_central_db)):
    email = normalize_email(str(body.email))
    admin = central.query(SaasSuperAdminORM).filter_by(email=email).first()
    if not admin or not admin.is_active or not verify_password(body.password, admin.hashed_password):
        record_login_event(email=email, success=False, detail="super_admin")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou mot de passe incorrect.")
    admin.last_login_at = datetime.utcnow()
    central.commit()
    token = create_access_token({"sub": admin.email, "actor": "super_admin", "user_type": "super_admin", "super_admin_id": admin.id})
    record_login_event(email=email, success=True, detail="super_admin")
    record_audit("super_admin", "super_admin_login", actor_email=email)
    return {"access_token": token, "token_type": "bearer", "workspace": "plateforme", "user_type": "super_admin"}


@router.get("/overview")
def platform_overview(admin: SaasSuperAdminORM = Depends(get_platform_admin), central: Session = Depends(get_central_db)):
    companies = central.query(CompanyRegistryORM).count()
    active = central.query(CompanyRegistryORM).filter_by(status="active").count()
    trialing = central.query(SaasSubscriptionORM).filter_by(status="trialing").count()
    licensed = central.query(SaasSubscriptionORM).filter_by(status="active").count()
    return {
        "workspace": "plateforme",
        "actor": admin.email,
        "companies_total": companies,
        "companies_active": active,
        "subscriptions_trialing": trialing,
        "subscriptions_active": licensed,
        "scope": "Registre SaaS uniquement. Les données métier restent dans la base de chaque entreprise.",
    }


@router.get("/companies")
def list_companies(admin: SaasSuperAdminORM = Depends(get_platform_admin), central: Session = Depends(get_central_db)):
    del admin
    rows = central.query(CompanyRegistryORM).order_by(CompanyRegistryORM.id.desc()).all()
    subscriptions = {item.tenant_id: item for item in central.query(SaasSubscriptionORM).all()}
    return [_company_view(company, subscriptions.get(company.tenant_id)) for company in rows]


@router.get("/audit")
def list_audit(admin: SaasSuperAdminORM = Depends(get_platform_admin), central: Session = Depends(get_central_db), limit: int = 30):
    del admin
    limit = min(max(limit, 1), 100)
    rows = central.query(SaasAuditLogORM).order_by(SaasAuditLogORM.id.desc()).limit(limit).all()
    return [
        {
            "actor_type": row.actor_type,
            "actor_email": row.actor_email,
            "action": row.action,
            "tenant_id": row.tenant_id,
            "detail": row.detail,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/login-history")
def list_login_history(admin: SaasSuperAdminORM = Depends(get_platform_admin), central: Session = Depends(get_central_db), limit: int = 30):
    del admin
    limit = min(max(limit, 1), 100)
    rows = central.query(SaasLoginEventORM).order_by(SaasLoginEventORM.id.desc()).limit(limit).all()
    return [
        {
            "email": row.email,
            "tenant_id": row.tenant_id,
            "success": row.success,
            "ip_address": row.ip_address,
            "detail": row.detail,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.post("/companies/{tenant_id}/grants", status_code=status.HTTP_201_CREATED)
def grant_company_access(
    tenant_id: str,
    body: AccessGrantIn,
    admin: SaasSuperAdminORM = Depends(get_platform_admin),
    central: Session = Depends(get_central_db),
):
    normalized = normalize_tenant_id(tenant_id)
    company = central.query(CompanyRegistryORM).filter_by(tenant_id=normalized).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entreprise inconnue.")
    grant = SaasAccessGrantORM(
        super_admin_id=admin.id,
        tenant_id=normalized,
        reason=body.reason.strip(),
        expires_at=datetime.utcnow() + timedelta(minutes=body.minutes),
    )
    central.add(grant)
    central.commit()
    central.refresh(grant)
    record_audit("super_admin", "support_grant_created", actor_email=admin.email, tenant_id=normalized, detail=body.reason.strip())
    return {"grant_id": grant.id, "tenant_id": normalized, "expires_at": grant.expires_at.isoformat()}


@router.post("/companies/{tenant_id}/enter")
def enter_company_environment(
    tenant_id: str,
    admin: SaasSuperAdminORM = Depends(get_platform_admin),
    central: Session = Depends(get_central_db),
):
    normalized = normalize_tenant_id(tenant_id)
    company = central.query(CompanyRegistryORM).filter_by(tenant_id=normalized, status="active").first()
    if not company:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Environnement d'entreprise inactif ou inconnu.")
    grant = (
        central.query(SaasAccessGrantORM)
        .filter(
            SaasAccessGrantORM.super_admin_id == admin.id,
            SaasAccessGrantORM.tenant_id == normalized,
            SaasAccessGrantORM.expires_at > datetime.utcnow(),
        )
        .order_by(SaasAccessGrantORM.id.desc())
        .first()
    )
    if not grant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Aucun accès exceptionnel en cours pour cette entreprise.")
    remaining = grant.expires_at - datetime.utcnow()
    token = create_access_token(
        {
            "sub": admin.email,
            "actor": "super_admin",
            "user_type": "super_admin",
            "super_admin_id": admin.id,
            "tenant_id": normalized,
            "support_grant_id": grant.id,
        },
        expires_delta=remaining,
    )
    record_audit("super_admin", "support_access_opened", actor_email=admin.email, tenant_id=normalized, detail=f"grant={grant.id}")
    return {
        "access_token": token,
        "token_type": "bearer",
        "workspace": "entreprise",
        "tenant_id": normalized,
        "database_name": company.database_name,
        "logical_database_name": company.logical_database_name,
        "environment_code": company.environment_code,
        "expires_at": grant.expires_at.isoformat(),
    }
