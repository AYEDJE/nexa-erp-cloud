import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import bcrypt
import pyotp
from fastapi import Header, HTTPException, Request, status
from jose import JWTError, jwt

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
    TEMP_TOKEN_EXPIRE_MINUTES,
)


# --- 1. HACHAGE & VÉRIFICATION DES MOTS DE PASSE ---
def normalize_email(email: str) -> str:
    """E-mail comparé sans tenir compte de la casse ni des espaces."""
    return (email or "").strip().lower()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8")[:72], salt).decode("utf-8")


# --- 2. GESTION DES JETONS JWT (Access, Refresh & Temp) ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "token_type": "access",
        "jti": str(uuid.uuid4())
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> Tuple[str, str, datetime]:
    """
    Retourne (refresh_token_jwt, jti_identifiant_session, date_expiration)
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "token_type": "refresh",
        "jti": jti
    })
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, jti, expire


def create_temp_2fa_token(data: dict) -> str:
    """Jeton temporaire délivré lors du login lorsque le 2FA est requis"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=TEMP_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "token_type": "temp_2fa"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide ou expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# --- 3. AUTHENTIFICATION MULTI-FACTEURS (MFA / 2FA - TOTP) ---

def generate_2fa_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer_name: str = "NexaERP Cloud") -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer_name)


def verify_totp_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    clean_code = code.strip().replace(" ", "")
    totp = pyotp.TOTP(secret)
    # valid_window=1 permet une tolérance d'horloge de +/- 30 secondes
    return totp.verify(clean_code, valid_window=1)


def generate_backup_codes(count: int = 8) -> List[str]:
    """Génère des codes de secours aléatoires à usage unique (ex: ABCD-1234)"""
    codes = []
    for _ in range(count):
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        codes.append(f"{part1}-{part2}")
    return codes


# --- 4. IDENTIFICATION TECHNIQUE DE L'APPAREIL & IP ---

def get_client_ip(request: Request) -> str:
    """Extrait l'adresse IP client avec prise en compte des reverse-proxies"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def parse_user_agent(ua_string: Optional[str]) -> Dict[str, str]:
    if not ua_string:
        return {"os": "Inconnu", "browser": "Inconnu", "device": "Appareil Inconnu"}

    ua = ua_string.lower()

    # Détection OS
    if "windows" in ua:
        os_name = "Windows"
    elif "macintosh" in ua or "mac os" in ua:
        os_name = "macOS"
    elif "iphone" in ua or "ipad" in ua:
        os_name = "iOS"
    elif "android" in ua:
        os_name = "Android"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Autre OS"

    # Détection Navigateur
    if "edg/" in ua or "edge" in ua:
        browser = "Microsoft Edge"
    elif "chrome/" in ua and "safari/" in ua and "edg/" not in ua:
        browser = "Google Chrome"
    elif "firefox/" in ua:
        browser = "Mozilla Firefox"
    elif "safari/" in ua and "chrome" not in ua:
        browser = "Apple Safari"
    elif "opera" in ua or "opr/" in ua:
        browser = "Opera"
    else:
        browser = "Navigateur Web"

    return {
        "os": os_name,
        "browser": browser,
        "device": f"{browser} sur {os_name}"
    }


def compute_device_fingerprint(ip: str, user_agent: str) -> str:
    """Calcule une empreinte de sécurité stable pour identifier l'appareil"""
    raw = f"{ip[:7]}_{user_agent[:40]}"
    import hashlib
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def get_current_tenant_id(x_tenant_id: str = Header(default=..., alias="X-Tenant-ID")) -> str:
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le header X-Tenant-ID est obligatoire pour cette action."
        )
    return x_tenant_id
