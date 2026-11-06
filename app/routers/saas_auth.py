from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.database import CentralSessionLocal, get_central_db
from app.core.security import (
    compute_device_fingerprint,
    create_access_token,
    create_refresh_token,
    create_temp_2fa_token,
    decode_jwt_token,
    generate_backup_codes,
    get_client_ip,
    get_password_hash,
    normalize_email,
    parse_user_agent,
    verify_password,
    verify_totp_code,
)
from app.core.tenant_db import get_tenant_sessionmaker, normalize_tenant_id
from app.models.security import UserDeviceORM, UserSessionORM
from app.models.tenant_registry import CompanyRegistryORM, TenantUserRegistryORM
from app.models.user import Token, UserCreate, UserORM, UserResponse
from app.schemas.user import TwoFactorVerifyRequest
from app.services.tenant_provisioning import provision_new_tenant

router = APIRouter(prefix="/auth", tags=["SaaS authentification"])


def _issue_session(user: UserORM, tenant_id: str, request: Request, db) -> dict:
    now = datetime.utcnow()
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")
    ua = parse_user_agent(user_agent)
    fingerprint = compute_device_fingerprint(client_ip, user_agent)
    device = db.query(UserDeviceORM).filter_by(user_id=user.id, device_identifier=fingerprint).first()
    if device and device.status == "blocked":
        raise HTTPException(status_code=403, detail="Cet appareil est bloqué.")
    if not device:
        db.add(UserDeviceORM(tenant_id=tenant_id, user_id=user.id, device_identifier=fingerprint, device_name=ua["device"], os=ua["os"], browser=ua["browser"], last_ip=client_ip, status="authorized"))
    else:
        device.last_seen = now
        device.last_ip = client_ip
    db.query(UserSessionORM).filter_by(user_id=user.id, is_revoked=False).update({"is_revoked": True})
    claims = {"sub": user.email, "tenant_id": tenant_id, "user_type": user.user_type, "user_id": user.id}
    refresh_token, jti, expiry = create_refresh_token(claims)
    access_token = create_access_token({**claims, "jti": jti})
    db.add(UserSessionORM(tenant_id=tenant_id, user_id=user.id, session_token=jti, device_id=fingerprint, ip_address=client_ip, user_agent=user_agent, os=ua["os"], browser=ua["browser"], expires_at=expiry))
    user.last_login_at = now
    user.last_login_ip = client_ip
    db.commit()
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "requires_2fa": False}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, central: Session = Depends(get_central_db)):
    email = normalize_email(str(user_in.email))
    tenant_id = normalize_tenant_id(user_in.tenant_id)
    if central.query(TenantUserRegistryORM).filter_by(email=email, tenant_id=tenant_id).first():
        raise HTTPException(status_code=400, detail="Cet utilisateur existe déjà dans cette entreprise.")
    if central.query(TenantUserRegistryORM).filter_by(email=email, is_active=True).first():
        raise HTTPException(status_code=409, detail="Cet e-mail est déjà utilisé. La connexion déterminera le tenant depuis le registre central.")

    company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id).first()
    if not company:
        provision_new_tenant(tenant_id, company_name=tenant_id)
    company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id, status="active").first()
    if not company:
        raise HTTPException(status_code=503, detail="L'environnement de l'entreprise n'a pas pu être activé.")

    db = get_tenant_sessionmaker(tenant_id)()
    try:
        if db.query(UserORM).filter_by(email=email).first():
            raise HTTPException(status_code=400, detail="Un utilisateur avec cet e-mail existe déjà.")
        user = UserORM(tenant_id=tenant_id, email=email, full_name=user_in.full_name, hashed_password=get_password_hash(user_in.password), user_type=user_in.user_type, is_active=True)
        db.add(user)
        db.flush()
        central.add(TenantUserRegistryORM(tenant_id=tenant_id, email=email, is_active=True))
        db.commit()
        central.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        central.rollback()
        raise
    finally:
        db.close()


@router.post("/login", response_model=Token)
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), central: Session = Depends(get_central_db)):
    email = normalize_email(form_data.username)
    mappings = central.query(TenantUserRegistryORM).filter_by(email=email, is_active=True).all()
    requested_tenant = request.headers.get("X-Tenant-ID")
    if requested_tenant:
        requested_tenant = normalize_tenant_id(requested_tenant)
        mappings = [mapping for mapping in mappings if mapping.tenant_id == requested_tenant]
    if len(mappings) != 1:
        detail = "Tenant requis: cet e-mail est associé à plusieurs entreprises." if mappings else "E-mail ou mot de passe incorrect."
        raise HTTPException(status_code=401, detail=detail)
    tenant_id = mappings[0].tenant_id
    company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id, status="active").first()
    if not company:
        raise HTTPException(status_code=403, detail="Entreprise inactive ou inconnue.")
    db = get_tenant_sessionmaker(tenant_id)()
    try:
        user = db.query(UserORM).filter_by(email=email, tenant_id=tenant_id).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="E-mail ou mot de passe incorrect.", headers={"WWW-Authenticate": "Bearer"})
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Compte utilisateur inactif.")
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise HTTPException(status_code=403, detail="Compte temporairement verrouillé.")
        if user.is_two_factor_enabled:
            temp = create_temp_2fa_token({"sub": user.email, "tenant_id": tenant_id, "user_id": user.id, "user_type": user.user_type})
            return {"requires_2fa": True, "temp_token": temp, "token_type": "bearer"}
        return _issue_session(user, tenant_id, request, db)
    finally:
        db.close()


@router.post("/2fa/verify-login", response_model=Token)
def verify_2fa_login(body: TwoFactorVerifyRequest, request: Request):
    payload = decode_jwt_token(body.temp_token)
    if payload.get("token_type") != "temp_2fa" or not payload.get("tenant_id"):
        raise HTTPException(status_code=401, detail="Jeton temporaire 2FA invalide.")
    tenant_id = normalize_tenant_id(payload["tenant_id"])
    central = CentralSessionLocal()
    try:
        company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id, status="active").first()
        if not company:
            raise HTTPException(status_code=403, detail="Entreprise inactive ou inconnue.")
    finally:
        central.close()
    db = get_tenant_sessionmaker(tenant_id)()
    try:
        user = db.query(UserORM).filter_by(id=payload.get("user_id"), email=normalize_email(payload.get("sub")), tenant_id=tenant_id).first()
        if not user or not user.is_active or not user.is_two_factor_enabled:
            raise HTTPException(status_code=401, detail="Utilisateur ou configuration 2FA invalide.")
        valid = verify_totp_code(user.two_factor_secret, body.code)
        if not valid and user.backup_codes:
            codes = [item.strip() for item in user.backup_codes.split(",") if item.strip()]
            submitted = body.code.strip().upper()
            if submitted in codes:
                codes.remove(submitted)
                user.backup_codes = ",".join(codes)
                valid = True
        if not valid:
            raise HTTPException(status_code=401, detail="Code 2FA invalide ou expiré.")
        return _issue_session(user, tenant_id, request, db)
    finally:
        db.close()


@router.post("/refresh", response_model=Token)
def refresh_access_token(body, central: Session = Depends(get_central_db)):
    payload = decode_jwt_token(body.refresh_token)
    if payload.get("token_type") != "refresh" or not payload.get("tenant_id"):
        raise HTTPException(status_code=401, detail="Jeton de rafraîchissement invalide.")
    tenant_id = normalize_tenant_id(payload["tenant_id"])
    company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id, status="active").first()
    if not company:
        raise HTTPException(status_code=403, detail="Entreprise inactive ou inconnue.")
    db = get_tenant_sessionmaker(tenant_id)()
    try:
        session = db.query(UserSessionORM).filter_by(session_token=payload.get("jti"), is_revoked=False).first()
        if not session or session.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Session expirée ou révoquée.")
        claims = {key: payload[key] for key in ("sub", "tenant_id", "user_type", "user_id")}
        access = create_access_token({**claims, "jti": payload["jti"]})
        db.commit()
        return {"access_token": access, "refresh_token": body.refresh_token, "token_type": "bearer", "requires_2fa": False}
    finally:
        db.close()
