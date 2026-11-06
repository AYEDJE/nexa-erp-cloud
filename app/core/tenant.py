from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.database import CentralSessionLocal
from app.core.tenant_db import normalize_tenant_id
from app.models.tenant_registry import CompanyRegistryORM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_tenant_id(token: str = Depends(oauth2_scheme)) -> str:
    if not token:
        raise HTTPException(status_code=401, detail="Jeton d'accès requis.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Jeton invalide ou expiré.") from exc
    if payload.get("token_type") != "access":
        raise HTTPException(status_code=401, detail="Un jeton d'accès est requis.")
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant absent du jeton.")
    tenant_id = normalize_tenant_id(tenant_id)
    central = CentralSessionLocal()
    try:
        company = central.query(CompanyRegistryORM).filter_by(tenant_id=tenant_id, status="active").first()
        if not company:
            raise HTTPException(status_code=403, detail="Entreprise inactive ou inconnue.")
    finally:
        central.close()
    return tenant_id


get_current_tenant_id = get_tenant_id
get_tenant = get_tenant_id
get_current_tenant = get_tenant_id
