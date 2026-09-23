from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

# Déclaration directe des clés pour le décodage du token
SECRET_KEY = "votre_cle_secrete_ultra_securisee_nexa_erp"
ALGORITHM = "HS256"

# Indique à FastAPI d'extraire le token depuis le header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_tenant(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dépendance FastAPI pour récupérer de manière sécurisée le tenant_id
    extrait du jeton JWT de l'utilisateur connecté.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants de session.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Décodage du token JWT avec la clé secrète
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        tenant_id: str = payload.get("tenant_id")
        
        if tenant_id is None:
            raise credentials_exception
            
        return tenant_id

    except JWTError:
        raise credentials_exception