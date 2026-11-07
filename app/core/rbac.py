from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.core.config import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Extrait et valide le payload du token JWT actif.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalide, expirée ou non fournie.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        if payload.get("token_type") not in (None, "access"):
            raise credentials_exception
        from app.services.session_guard import assert_active_session
        assert_active_session(payload)
        return payload
    except HTTPException:
        raise
    except (JWTError, Exception):
        raise credentials_exception


def canonical_user_type(value) -> str:
    """Ramène admin / UserType.ADMIN / Administrateur à la valeur métier 'admin'."""
    raw = getattr(value, "value", value)
    text = str(raw or "").strip().lower()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return {
        "administrateur": "admin",
        "administrator": "admin",
        "superadmin": "super_admin",
        "super-admin": "super_admin",
    }.get(text, text)


def _role_from_tenant(current_user: dict) -> str:
    """Le rôle réel est celui enregistré dans la base de l'entreprise, pas seulement le jeton."""
    tenant_id = current_user.get("tenant_id")
    email = str(current_user.get("sub") or "").strip().lower()
    if not tenant_id or not email:
        return ""
    try:
        from app.core.tenant_db import get_tenant_sessionmaker
        from app.models.user import UserORM

        db = get_tenant_sessionmaker(tenant_id)()
        try:
            user = db.query(UserORM).filter(UserORM.email == email, UserORM.tenant_id == tenant_id).first()
            return canonical_user_type(user.user_type) if user else ""
        finally:
            db.close()
    except Exception:
        return ""


class RoleChecker:
    """
    Dépendance FastAPI pour restreindre l'accès à une route
    selon les rôles autorisés (ex: 'admin', 'super_admin', 'staff').
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_user)) -> dict:
        role = canonical_user_type(current_user.get("user_type"))
        if role not in self.allowed_roles:
            role = _role_from_tenant(current_user)
        if role not in self.allowed_roles:
            email = current_user.get("sub") or "ce compte"
            label = {"staff": "collaborateur", "external": "utilisateur externe"}.get(role, role or "collaborateur")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Seul l'administrateur de l'entreprise peut gérer les collaborateurs. "
                    f"Le compte {email} est connecté en tant que « {label} »."
                ),
            )
        current_user["user_type"] = role
        return current_user
