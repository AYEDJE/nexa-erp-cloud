import json
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import LOCKOUT_DURATION_MINUTES, MAX_FAILED_LOGIN_ATTEMPTS
from app.core.database import get_db
from app.core.rbac import get_current_user
from app.core.security import (
    compute_device_fingerprint,
    create_access_token,
    create_refresh_token,
    create_temp_2fa_token,
    decode_jwt_token,
    generate_2fa_secret,
    generate_backup_codes,
    get_client_ip,
    get_password_hash,
    get_totp_uri,
    parse_user_agent,
    verify_password,
    verify_totp_code,
)
from app.models.security import (
    DeviceResponse,
    SecurityAlertORM,
    SessionResponse,
    UserDeviceORM,
    UserSessionORM,
)
from app.models.user import Token, UserCreate, UserORM, UserResponse
from app.schemas.user import (
    RefreshTokenRequest,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentification & Sécurité"])


# --- 1. INSCRIPTION ---

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(UserORM).filter(UserORM.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet e-mail existe déjà.",
        )

    hashed_pwd = get_password_hash(user_in.password)
    new_user = UserORM(
        tenant_id=user_in.tenant_id,
        email=user_in.email,
        hashed_password=hashed_pwd,
        user_type=user_in.user_type,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# --- 2. CONNEXION AVEC BRUTE-FORCE & DÉTECTION D'APPAREIL ---

@router.post("/login", response_model=Token)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    client_ip = get_client_ip(request)
    ua_info = parse_user_agent(request.headers.get("User-Agent"))
    device_fp = compute_device_fingerprint(client_ip, request.headers.get("User-Agent", ""))

    user = db.query(UserORM).filter(UserORM.email == form_data.username).first()

    # Protection contre le Brute Force (Vérification de verrouillage de compte)
    if user and user.locked_until and user.locked_until > datetime.utcnow():
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60) + 1
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Compte temporairement verrouillé suite à plusieurs échecs. Réessayez dans {remaining} minute(s).",
        )

    if not user or not verify_password(form_data.password, user.hashed_password):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                # Alerte de sécurité
                alert = SecurityAlertORM(
                    tenant_id=user.tenant_id,
                    user_id=user.id,
                    alert_type="brute_force",
                    severity="high",
                    ip_address=client_ip,
                    details=json.dumps({"attempts": user.failed_login_attempts, "os": ua_info["os"]}),
                )
                db.add(alert)
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compte utilisateur inactif.",
        )

    # Réinitialisation des tentatives de brute-force après mot de passe correct
    user.failed_login_attempts = 0
    user.locked_until = None

    # Contrôle de l'appareil : vérification si bloqué
    device = db.query(UserDeviceORM).filter(
        UserDeviceORM.user_id == user.id,
        UserDeviceORM.device_identifier == device_fp
    ).first()

    if device and device.status == "blocked":
        # Alerte tentative d'accès via appareil bloqué
        alert = SecurityAlertORM(
            tenant_id=user.tenant_id,
            user_id=user.id,
            alert_type="blocked_device_access",
            severity="high",
            ip_address=client_ip,
            details=json.dumps({"device_name": device.device_name}),
        )
        db.add(alert)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cet appareil a été bloqué par mesure de sécurité. Contactez votre administrateur.",
        )

    # Détection de connexion inhabituelle (Changement d'IP)
    if user.last_login_ip and user.last_login_ip != client_ip:
        alert = SecurityAlertORM(
            tenant_id=user.tenant_id,
            user_id=user.id,
            alert_type="suspicious_login",
            severity="medium",
            ip_address=client_ip,
            details=json.dumps({
                "previous_ip": user.last_login_ip,
                "current_ip": client_ip,
                "browser": ua_info["browser"],
                "os": ua_info["os"]
            }),
        )
        db.add(alert)

    # Si 2FA est activé sur le compte, émettre un token temporaire intermédiaire
    if user.is_two_factor_enabled:
        temp_token = create_temp_2fa_token({
            "sub": user.email,
            "tenant_id": user.tenant_id,
            "user_id": user.id,
            "user_type": user.user_type,
            "device_fp": device_fp
        })
        db.commit()
        return {
            "requires_2fa": True,
            "temp_token": temp_token,
            "token_type": "bearer"
        }

    # Mise à jour de l'appareil
    if not device:
        device = UserDeviceORM(
            tenant_id=user.tenant_id,
            user_id=user.id,
            device_identifier=device_fp,
            device_name=ua_info["device"],
            os=ua_info["os"],
            browser=ua_info["browser"],
            last_ip=client_ip,
            status="authorized"
        )
        db.add(device)
    else:
        device.last_seen = datetime.utcnow()
        device.last_ip = client_ip

    # Création des jetons JWT
    payload_base = {
        "sub": user.email,
        "tenant_id": user.tenant_id,
        "user_type": user.user_type,
        "user_id": user.id,
    }
    refresh_token, jti, refresh_exp = create_refresh_token(payload_base)
    payload_base["jti"] = jti
    access_token = create_access_token(payload_base)

    # Enregistrement de la session active
    new_session = UserSessionORM(
        tenant_id=user.tenant_id,
        user_id=user.id,
        session_token=jti,
        device_id=device_fp,
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent", ""),
        os=ua_info["os"],
        browser=ua_info["browser"],
        expires_at=refresh_exp,
    )
    db.add(new_session)

    user.last_login_at = datetime.utcnow()
    user.last_login_ip = client_ip

    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "requires_2fa": False
    }


# --- 3. VALIDATION DU 2FA LORS DU LOGIN ---

@router.post("/2fa/verify-login", response_model=Token)
def verify_2fa_login(
    req_body: TwoFactorVerifyRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    if not req_body.temp_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le jeton temporaire temp_token est obligatoire.",
        )

    payload = decode_jwt_token(req_body.temp_token)
    if payload.get("token_type") != "temp_2fa":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jeton temporaire invalide pour cette étape.",
        )

    user = db.query(UserORM).filter(UserORM.email == payload.get("sub")).first()
    if not user or not user.is_two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA non configuré pour cet utilisateur.",
        )

    # Vérification code TOTP
    code_valid = verify_totp_code(user.two_factor_secret, req_body.code)

    # Vérification code de secours si TOTP échoue
    if not code_valid and user.backup_codes:
        backup_list = [c.strip() for c in user.backup_codes.split(",") if c.strip()]
        if req_body.code.strip().upper() in backup_list:
            code_valid = True
            backup_list.remove(req_body.code.strip().upper())
            user.backup_codes = ",".join(backup_list)

    if not code_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Code 2FA invalide ou expiré.",
        )

    client_ip = get_client_ip(request)
    ua_info = parse_user_agent(request.headers.get("User-Agent"))
    device_fp = payload.get("device_fp") or compute_device_fingerprint(client_ip, request.headers.get("User-Agent", ""))

    payload_base = {
        "sub": user.email,
        "tenant_id": user.tenant_id,
        "user_type": user.user_type,
        "user_id": user.id,
    }
    refresh_token, jti, refresh_exp = create_refresh_token(payload_base)
    payload_base["jti"] = jti
    access_token = create_access_token(payload_base)

    new_session = UserSessionORM(
        tenant_id=user.tenant_id,
        user_id=user.id,
        session_token=jti,
        device_id=device_fp,
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent", ""),
        os=ua_info["os"],
        browser=ua_info["browser"],
        expires_at=refresh_exp,
    )
    db.add(new_session)

    user.last_login_at = datetime.utcnow()
    user.last_login_ip = client_ip

    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "requires_2fa": False
    }


# --- 4. CONFIGURATION ET GESTION DU 2FA ---

@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def setup_two_factor(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(UserORM).filter(UserORM.email == current_user["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    secret = generate_2fa_secret()
    backup_codes = generate_backup_codes(8)
    otp_uri = get_totp_uri(secret, email=user.email)

    user.two_factor_secret = secret
    user.backup_codes = ",".join(backup_codes)
    db.commit()

    return {
        "secret": secret,
        "otpauth_url": otp_uri,
        "backup_codes": backup_codes
    }


@router.post("/2fa/enable")
def enable_two_factor(
    body: TwoFactorVerifyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(UserORM).filter(UserORM.email == current_user["sub"]).first()
    if not user or not user.two_factor_secret:
        raise HTTPException(status_code=400, detail="Veuillez d'abord initialiser le 2FA via /auth/2fa/setup.")

    if not verify_totp_code(user.two_factor_secret, body.code):
        raise HTTPException(status_code=400, detail="Code de validation TOTP incorrect.")

    user.is_two_factor_enabled = True
    db.commit()
    return {"message": "Authentification à deux facteurs (2FA) activée avec succès."}


@router.post("/2fa/disable")
def disable_two_factor(
    body: TwoFactorVerifyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(UserORM).filter(UserORM.email == current_user["sub"]).first()
    if not user or not user.is_two_factor_enabled:
        raise HTTPException(status_code=400, detail="Le 2FA n'est pas activé sur ce compte.")

    if not verify_totp_code(user.two_factor_secret, body.code):
        raise HTTPException(status_code=400, detail="Code incorrect.")

    user.is_two_factor_enabled = False
    user.two_factor_secret = None
    user.backup_codes = None
    db.commit()
    return {"message": "Authentification à deux facteurs désactivée."}


# --- 5. RENOUVELLEMENT DE JETON & DÉCONNEXION ---

@router.post("/refresh", response_model=Token)
def refresh_access_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_jwt_token(body.refresh_token)
    if payload.get("token_type") != "refresh":
        raise HTTPException(status_code=400, detail="Jeton de rafraîchissement invalide.")

    jti = payload.get("jti")
    session = db.query(UserSessionORM).filter(
        UserSessionORM.session_token == jti,
        UserSessionORM.is_revoked == False
    ).first()

    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée ou révoquée. Veuillez vous reconnecter.",
        )

    # Mise à jour activité
    session.last_active_at = datetime.utcnow()

    # Création du nouvel Access Token
    new_access_token = create_access_token({
        "sub": payload["sub"],
        "tenant_id": payload["tenant_id"],
        "user_type": payload["user_type"],
        "user_id": payload["user_id"],
        "jti": jti
    })

    db.commit()
    return {
        "access_token": new_access_token,
        "refresh_token": body.refresh_token,
        "token_type": "bearer",
        "requires_2fa": False
    }


@router.post("/logout")
def logout_user(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    jti = current_user.get("jti")
    if jti:
        session = db.query(UserSessionORM).filter(UserSessionORM.session_token == jti).first()
        if session:
            session.is_revoked = True
            db.commit()
    return {"message": "Déconnexion réussie. Session révoquée."}


# --- 6. GESTION DES SESSIONS ACTIVES DE L'UTILISATEUR ---

@router.get("/sessions", response_model=List[SessionResponse])
def get_user_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(UserSessionORM).filter(
        UserSessionORM.user_id == current_user["user_id"],
        UserSessionORM.is_revoked == False,
        UserSessionORM.expires_at > datetime.utcnow()
    ).order_by(UserSessionORM.last_active_at.desc()).all()
    return sessions


@router.delete("/sessions/{session_id}")
def revoke_single_session(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(UserSessionORM).filter(
        UserSessionORM.id == session_id,
        UserSessionORM.user_id == current_user["user_id"]
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable.")

    session.is_revoked = True
    db.commit()
    return {"message": f"Session {session_id} révoquée avec succès."}


@router.delete("/sessions")
def revoke_other_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_jti = current_user.get("jti")
    sessions = db.query(UserSessionORM).filter(
        UserSessionORM.user_id == current_user["user_id"],
        UserSessionORM.session_token != current_jti,
        UserSessionORM.is_revoked == False
    ).all()

    for s in sessions:
        s.is_revoked = True

    db.commit()
    return {"message": f"{len(sessions)} autre(s) session(s) révoquée(s)."}
