from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import CentralSessionLocal, get_central_db
from app.core.security import (
    compute_device_fingerprint,
    create_access_token,
    create_refresh_token,
    create_temp_2fa_token,
    get_client_ip,
    get_password_hash,
    normalize_email,
    parse_user_agent,
    verify_password,
)
from app.core.tenant_db import get_tenant_sessionmaker, normalize_tenant_id
from app.models.rbac import RoleORM
from app.models.tenant_registry import CompanyRegistryORM, TenantUserRegistryORM
from app.models.user import Token, UserCreate, UserORM, UserResponse, UserType
from app.models.security import UserDeviceORM, UserSessionORM
from app.services.saas_platform_service import ALLOWED_PLANS, record_login_event
from app.services.tenant_provisioning import provision_new_tenant

router = APIRouter(prefix="/auth", tags=["SaaS authentification"])


def _workspace_payload(company: CompanyRegistryORM, user_type: str) -> dict:
    return {
        "tenant_id": company.tenant_id,
        "company_name": company.company_name,
        "database_name": company.database_name,
        "logical_database_name": company.logical_database_name,
        "environment_code": company.environment_code,
        "user_type": user_type,
        "workspace": "entreprise",
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, central: Session = Depends(get_central_db)):
    email = normalize_email(str(user_in.email))
    tenant_id = normalize_tenant_id(user_in.tenant_id)
    if user_in.user_type == UserType.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Le super administrateur est un compte de la plateforme, pas un utilisateur d'entreprise.")
    plan = (user_in.plan or "trial").strip().lower()
    if plan not in ALLOWED_PLANS:
        raise HTTPException(status_code=422, detail="Formule inconnue. Valeurs acceptées : trial, business, enterprise.")
    if central.query(TenantUserRegistryORM).filter_by(email=email, tenant_id=tenant_id).first():
        raise HTTPException(status_code=400, detail="Cet utilisateur existe déjà dans cette entreprise.")

    company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id).first()
    if company is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"L'entreprise « {company.company_name} » existe déjà. "
                "Une nouvelle inscription ne rejoint pas une entreprise existante. "
                "Choisissez un autre nom, ou connectez-vous pour ajouter un collaborateur depuis l'espace de cette entreprise."
            ),
        )
    if user_in.user_type != UserType.ADMIN:
        raise HTTPException(status_code=422, detail="Le premier compte d'une entreprise doit être son administrateur.")
    provision_new_tenant(
        tenant_id,
        company_name=user_in.company_name or tenant_id,
        plan=plan,
        legal_form=user_in.legal_form,
        tax_id=user_in.tax_id,
        activity=user_in.activity,
    )
    company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id).first()

    factory = get_tenant_sessionmaker(tenant_id)
    tenant_db = factory()
    try:
        existing = tenant_db.query(UserORM).filter(UserORM.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Un utilisateur avec cet e-mail existe déjà dans cette entreprise.")
        user = UserORM(
            tenant_id=tenant_id,
            email=email,
            full_name=user_in.full_name,
            hashed_password=get_password_hash(user_in.password),
            user_type=user_in.user_type,
            is_active=True,
        )
        tenant_db.add(user)
        tenant_db.flush()
        if user.user_type == UserType.ADMIN or str(getattr(user.user_type, "value", user.user_type)) == UserType.ADMIN.value:
            admin_role = tenant_db.query(RoleORM).filter_by(tenant_id=tenant_id, name="Administrateur d'entreprise").first()
            if admin_role:
                user.role_id = admin_role.id
        central.add(TenantUserRegistryORM(tenant_id=tenant_id, email=email, is_active=True))
        tenant_db.commit()
        central.commit()
        tenant_db.refresh(user)
        return user
    except Exception:
        tenant_db.rollback()
        central.rollback()
        raise
    finally:
        tenant_db.close()


@router.post("/login", response_model=Token)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    central: Session = Depends(get_central_db),
):
    email = normalize_email(form_data.username)
    mappings = central.query(TenantUserRegistryORM).filter_by(email=email, is_active=True).all()
    requested_tenant = request.headers.get("X-Tenant-ID")
    if requested_tenant:
        requested_tenant = normalize_tenant_id(requested_tenant)
        mappings = [mapping for mapping in mappings if mapping.tenant_id == requested_tenant]
    if len(mappings) != 1:
        detail = "Tenant requis: cet e-mail est associé à plusieurs entreprises." if mappings else "E-mail ou mot de passe incorrect."
        record_login_event(email=email, success=False, ip_address=get_client_ip(request), detail="routing")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

    tenant_id = mappings[0].tenant_id
    company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id, status="active").first()
    if not company:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="L'environnement de cette entreprise n'est pas actif.")

    tenant_db = get_tenant_sessionmaker(tenant_id)()
    try:
        user = tenant_db.query(UserORM).filter(UserORM.email == email, UserORM.tenant_id == tenant_id).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            record_login_event(email=email, tenant_id=tenant_id, success=False, ip_address=get_client_ip(request), detail="credentials")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou mot de passe incorrect.", headers={"WWW-Authenticate": "Bearer"})
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte utilisateur inactif.")

        from app.core.rbac import canonical_user_type
        user_type = canonical_user_type(user.user_type)
        if user.is_two_factor_enabled:
            temp_token = create_temp_2fa_token({"sub": user.email, "tenant_id": tenant_id, "user_id": user.id, "user_type": user_type})
            record_login_event(email=email, tenant_id=tenant_id, success=True, ip_address=get_client_ip(request), detail="2fa_challenge")
            return {"requires_2fa": True, "temp_token": temp_token, "token_type": "bearer", **_workspace_payload(company, user_type)}

        client_ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        ua = parse_user_agent(user_agent)
        device_fp = compute_device_fingerprint(client_ip, user_agent)
        device = tenant_db.query(UserDeviceORM).filter_by(user_id=user.id, device_identifier=device_fp).first()
        if device and device.status == "blocked":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cet appareil est bloqué.")
        if not device:
            tenant_db.add(UserDeviceORM(tenant_id=tenant_id, user_id=user.id, device_identifier=device_fp, device_name=ua["device"], os=ua["os"], browser=ua["browser"], last_ip=client_ip, status="authorized"))
        else:
            device.last_seen = __import__("datetime").datetime.utcnow()
            device.last_ip = client_ip

        now = __import__("datetime").datetime.utcnow()
        user.failed_login_attempts = 0
        user.locked_until = None
        refresh_token, jti, refresh_exp = create_refresh_token({"sub": user.email, "tenant_id": tenant_id, "user_type": user_type, "user_id": user.id})
        access_token = create_access_token({"sub": user.email, "tenant_id": tenant_id, "user_type": user_type, "user_id": user.id, "jti": jti})
        tenant_db.add(UserSessionORM(tenant_id=tenant_id, user_id=user.id, session_token=jti, device_id=device_fp, ip_address=client_ip, user_agent=user_agent, os=ua["os"], browser=ua["browser"], expires_at=refresh_exp))
        user.last_login_at = now
        user.last_login_ip = client_ip
        tenant_db.commit()
        record_login_event(email=email, tenant_id=tenant_id, success=True, ip_address=client_ip, detail="workspace")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "requires_2fa": False,
            **_workspace_payload(company, user_type),
        }
    finally:
        tenant_db.close()
