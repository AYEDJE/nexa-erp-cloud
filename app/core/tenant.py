from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

SECRET_KEY = "votre_cle_secrete_ultra_securisee_nexa_erp"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_tenant_id(
    token: str = Depends(oauth2_scheme),
    x_tenant_id: str = Header(None, alias="X-Tenant-ID")
) -> str:
    """
    Extrait le tenant_id :
    1. Depuis le token JWT s'il est présent (Comportement Prod Sécurisé)
    2. Sinon depuis le header HTTP 'X-Tenant-ID' (Comportement Dev/Tests)
    3. Lève une erreur 401 si aucun des deux n'est fourni.
    """
    # 1. Tentative d'extraction via JWT Token
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            tenant_id: str = payload.get("tenant_id")
            if tenant_id:
                return tenant_id
        except JWTError:
            pass  # Si le token est invalide, on regarde l'en-tête de secours

    # 2. Secours via Header X-Tenant-ID (pour les tests rapides)
    if x_tenant_id and x_tenant_id.strip() != "":
        return x_tenant_id

    # 3. Si ni token ni header valide n'est fourni
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identification multi-tenant requise (Token JWT ou en-tête 'X-Tenant-ID' manquant).",
        headers={"WWW-Authenticate": "Bearer"},
    )

get_current_tenant_id = get_tenant_id
get_tenant = get_tenant_id
get_current_tenant = get_tenant_id