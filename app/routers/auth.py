import json
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
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
    normalize_email,
    parse_user_agent,
    verify_password,
    verify_totp_code,
)
from app.models.security import (
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

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    # Stocke les nouvelles adresses toujours en minuscules et sans espaces périphériques.
    email = normalize_email(str(user_in.email))

    # Évite les doublons, y compris si un ancien compte contient une casse différente.
    existing_user = db.query(UserORM).filter(
        func.lower(func.trim(UserORM.email)) == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet e-mail existe déjà.",
        )

    new_user = UserORM(
        tenant_id=user_in.tenant_id.strip(),
        email=email,
        hashed_password=get_password_hash(user_in.password),
        user_type=user_in.user_type,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# --- 2. CONNEXION AVEC PROTECTION BRUTE FORCE ET DÉTECTION D'APPAREIL ---

@router.post("/login", response_model=Token)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")
    ua_info = parse_user_agent(user_agent)
    device_fp = compute_device_fingerprint(client_ip, user_agent)

    # La recherche ignore les majuscules et les espaces autour de l'e-mail.
    email = normalize_email(form_data.username)
    user = db.query(UserORM).filter(
        func.lower(func.trim(UserORM.email)) == email
    ).first()

    if user and user.locked_until and user.locked_until > datetime.utcnow():
        remaining = int(
            (user.locked_until - datetime.utcnow()).total_seconds() / 60
        ) + 1
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Compte temporairement verrouillé suite à plusieurs échecs. "
                f"Réessayez dans {remaining} minute(s)."
            ),
        )

    if not user or not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        if user:
            user.failed_login_attempts = (
                user.failed_login_attempts or 0
            ) + 1

            if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(
                    minutes=LOCKOUT_DURATION_MINUTES
                )
                db.add(
                    SecurityAlertORM(
                        tenant_id=user.tenant_id,
                        user_id=user.id,
                        alert_type="brute_force",
                        severity="high",
                        ip_address=client_ip,
                        details=json.dumps({
                            "attempts": user.failed_login_attempts,
                            "os": ua_info["os"],
                        }),
                    )
                )

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

    # Réinitialise le compteur après une connexion réussie.
    user.failed_login_attempts = 0
    user.locked_until = None

    device = db.query(UserDeviceORM).filter(
        UserDeviceORM.user_id == user.id,
        UserDeviceORM.device_identifier == device_fp,
    ).first()

    if device and device.status == "blocked":
        db.add(
            SecurityAlertORM(
                tenant_id=user.tenant_id,
                user_id=user.id,
                alert_type="blocked_device_access",
                severity="high",
                ip_address=client_ip,
                details=json.dumps({"device_name": device.device_name}),
            )
        )
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Cet appareil a été bloqué par mesure de sécurité. "
                "Contactez votre administrateur."
            ),
        )

    if user.last_login_ip and user.last_login_ip != client_ip:
        db.add(
            SecurityAlertORM(
                tenant_id=user.tenant_id,
                user_id=user.id,
                alert_type="suspicious_login",
                severity="medium",
                ip_address=client_ip,
                details=json.dumps({
                    "previous_ip": user.last_login_ip,
                    "current_ip": client_ip,
                    "browser": ua_info["browser"],
                    "os": ua_info["os"],
                }),
            )
        )

    # Si le 2FA est activé, renvoie un jeton temporaire.
    if user.is_two_factor_enabled:
        temp_token = create_temp_2fa_token({
            "sub": user.email,
            "tenant_id": user.tenant_id,
            "user_id": user.id,
            "user_type": user.user_type,
            "device_fp": device_fp,
        })
        db.commit()
        return {
            "requires_2fa": True,
            "temp_token": temp_token,
            "token_type": "bearer",
        }

    if not device:
        device = UserDeviceORM(
            tenant_id=user.tenant_id,
            user_id=user.id,
            device_identifier=device_fp,
            device_name=ua_info["device"],
            os=ua_info["os"],
            browser=ua_info["browser"],
            last_ip=client_ip,
            status="authorized",
        )
        db.add(device)
    else:
        device.last_seen = datetime.utcnow()
        device.last_ip = client_ip

    payload_base = {
        "sub": user.email,
        "tenant_id": user.tenant_id,
        "user_type": user.user_type,
        "user_id": user.id,
    }

    refresh_token, jti, refresh_exp = create_refresh_token(payload_base)
    payload_base["jti"] = jti
    access_token = create_access_token(payload_base)

    db.add(
        UserSessionORM(
            tenant_id=user.tenant_id,
            user_id=user.id,
            session_token=jti,
            device_id=device_fp,
            ip_address=client_ip,
            user_agent=user_agent,
            os=ua_info["os"],
            browser=ua_info["browser"],
            expires_at=refresh_exp,
        )
    )

    user.last_login_at = datetime.utcnow()
    user.last_login_ip = client_ip

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "requires_2fa": False,
    }


# --- 3. VALIDATION DU 2FA LORS DE LA CONNEXION ---

@router.post("/2fa/verify-login", response_model=Token)
def verify_2fa_login(
    req_body: TwoFactorVerifyRequest,
    request: Request,
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
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Entreprise absente du jeton temporaire.",
        )

    from app.core.tenant_db import get_tenant_sessionmaker
    db = get_tenant_sessionmaker(tenant_id)()
    try:
        return _complete_2fa_login(req_body, request, db, payload)
    finally:
        db.close()


def _complete_2fa_login(req_body, request, db, payload):
    user = db.query(UserORM).filter(
        UserORM.email == payload.get("sub"),
        UserORM.tenant_id == payload.get("tenant_id"),
    ).first()

    if not user or not user.is_two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA non configuré pour cet utilisateur.",
        )

    code_valid = verify_totp_code(user.two_factor_secret, req_body.code)

    # Vérifie aussi les codes de secours à usage unique.
    if not code_valid and user.backup_codes:
        backup_list = [
            code.strip()
            for code in user.backup_codes.split(",")
            if code.strip()
        ]
        submitted_code = req_body.code.strip().upper()

        if submitted_code in backup_list:
            code_valid = True
            backup_list.remove(submitted_code)
            user.backup_codes = ",".join(backup_list)

    if not code_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Code 2FA invalide ou expiré.",
        )

    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")
    ua_info = parse_user_agent(user_agent)
    device_fp = payload.get("device_fp") or compute_device_fingerprint(
        client_ip,
        user_agent,
    )

    payload_base = {
        "sub": user.email,
        "tenant_id": user.tenant_id,
        "user_type": user.user_type,
        "user_id": user.id,
    }

    refresh_token, jti, refresh_exp = create_refresh_token(payload_base)
    payload_base["jti"] = jti
    access_token = create_access_token(payload_base)

    db.add(
        UserSessionORM(
            tenant_id=user.tenant_id,
            user_id=user.id,
            session_token=jti,
            device_id=device_fp,
            ip_address=client_ip,
            user_agent=user_agent,
            os=ua_info["os"],
            browser=ua_info["browser"],
            expires_at=refresh_exp,
        )
    )

    user.last_login_at = datetime.utcnow()
    user.last_login_ip = client_ip

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "requires_2fa": False,
    }


# --- 4. CONFIGURATION ET GESTION DU 2FA ---

@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def setup_two_factor(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(UserORM).filter(
        UserORM.email == current_user["sub"]
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable.",
        )

    secret = generate_2fa_secret()
    backup_codes = generate_backup_codes(8)
    otp_uri = get_totp_uri(secret, email=user.email)

    user.two_factor_secret = secret
    user.backup_codes = ",".join(backup_codes)
    db.commit()

    return {
        "secret": secret,
        "otpauth_url": otp_uri,
        "backup_codes": backup_codes,
    }


@router.post("/2fa/enable")
def enable_two_factor(
    body: TwoFactorVerifyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(UserORM).filter(
        UserORM.email == current_user["sub"]
    ).first()

    if not user or not user.two_factor_secret:
        raise HTTPException(
            status_code=400,
            detail="Veuillez d'abord initialiser le 2FA via /auth/2fa/setup.",
        )

    if not verify_totp_code(user.two_factor_secret, body.code):
        raise HTTPException(
            status_code=400,
            detail="Code de validation TOTP incorrect.",
        )

    user.is_two_factor_enabled = True
    db.commit()

    return {
        "message": "Authentification à deux facteurs (2FA) activée avec succès."
    }


@router.post("/2fa/disable")
def disable_two_factor(
    body: TwoFactorVerifyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(UserORM).filter(
        UserORM.email == current_user["sub"]
    ).first()

    if not user or not user.is_two_factor_enabled:
        raise HTTPException(
            status_code=400,
            detail="Le 2FA n'est pas activé sur ce compte.",
        )

    if not verify_totp_code(user.two_factor_secret, body.code):
        raise HTTPException(
            status_code=400,
            detail="Code incorrect.",
        )

    user.is_two_factor_enabled = False
    user.two_factor_secret = None
    user.backup_codes = None
    db.commit()

    return {
        "message": "Authentification à deux facteurs désactivée."
    }


# --- 5. RENOUVELLEMENT DE JETON ET DÉCONNEXION ---

@router.post("/refresh", response_model=Token)
def refresh_access_token(
    body: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    payload = decode_jwt_token(body.refresh_token)

    if payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=400,
            detail="Jeton de rafraîchissement invalide.",
        )

    jti = payload.get("jti")
    session = db.query(UserSessionORM).filter(
        UserSessionORM.session_token == jti,
        UserSessionORM.is_revoked == False,
    ).first()

    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée ou révoquée. Veuillez vous reconnecter.",
        )

    session.last_active_at = datetime.utcnow()

    new_access_token = create_access_token({
        "sub": payload["sub"],
        "tenant_id": payload["tenant_id"],
        "user_type": payload["user_type"],
        "user_id": payload["user_id"],
        "jti": jti,
    })

    db.commit()

    return {
        "access_token": new_access_token,
        "refresh_token": body.refresh_token,
        "token_type": "bearer",
        "requires_2fa": False,
    }


@router.post("/logout")
def logout_user(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    jti = current_user.get("jti")

    if jti:
        session = db.query(UserSessionORM).filter(
            UserSessionORM.session_token == jti
        ).first()

        if session:
            session.is_revoked = True
            db.commit()

    return {"message": "Déconnexion réussie. Session révoquée."}


# --- 6. GESTION DES SESSIONS ACTIVES ---

@router.get("/sessions", response_model=List[SessionResponse])
def get_user_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(UserSessionORM).filter(
        UserSessionORM.user_id == current_user["user_id"],
        UserSessionORM.is_revoked == False,
        UserSessionORM.expires_at > datetime.utcnow(),
    ).order_by(
        UserSessionORM.last_active_at.desc()
    ).all()


@router.delete("/sessions/{session_id}")
def revoke_single_session(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(UserSessionORM).filter(
        UserSessionORM.id == session_id,
        UserSessionORM.user_id == current_user["user_id"],
    ).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session introuvable.",
        )

    session.is_revoked = True
    db.commit()

    return {"message": f"Session {session_id} révoquée avec succès."}


@router.delete("/sessions")
def revoke_other_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_jti = current_user.get("jti")

    sessions = db.query(UserSessionORM).filter(
        UserSessionORM.user_id == current_user["user_id"],
        UserSessionORM.session_token != current_jti,
        UserSessionORM.is_revoked == False,
    ).all()

    for session in sessions:
        session.is_revoked = True

    db.commit()

    return {"message": f"{len(sessions)} autre(s) session(s) révoquée(s)."}