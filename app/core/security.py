from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from fastapi import Header, HTTPException
from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Configuration du moteur de hachage de mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 1. Vérifier si un mot de passe soumis correspond au hachage stocké
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# 2. Convertir un mot de passe en clair en empreinte sécurisée (hachage)
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# 3. Générer le jeton d'accès JWT avec expiration
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_tenant_id(x_tenant_id: str = Header(default=..., alias="X-Tenant-ID")) -> str:
    """
    Récupère l'ID du tenant depuis les headers de la requête HTTP.
    Bloque la requête (Erreur 400) si le header est manquant.
    """
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Le header X-Tenant-ID est obligatoire pour cette action.")
    
    return x_tenant_id