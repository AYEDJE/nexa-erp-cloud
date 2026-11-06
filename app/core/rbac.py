from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.database import CentralSessionLocal
from app.core.tenant_db import normalize_tenant_id
from app.models.tenant_registry import CompanyRegistryORM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    exception = HTTPException(status_code=401, detail="Session invalide, expirée ou non fournie.", headers={"WWW-Authenticate": "Bearer"})
    if not token:
        raise exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise exception from exc
    if payload.get("token_type") != "access" or not payload.get("sub") or not payload.get("tenant_id"):
        raise exception
    tenant_id = normalize_tenant_id(payload["tenant_id"])
    central = CentralSessionLocal()
    try:
        company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id, status="active").first()
        if not company:
            raise HTTPException(status_code=403, detail="Entreprise inactive ou inconnue.")
    finally:
        central.close()
    payload["tenant_id"] = tenant_id
    return payload


class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("user_type") not in self.allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissions insuffisantes pour accéder à cette ressource.")
        return current_user
