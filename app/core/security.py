from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from passlib.context import CryptContext

# Clé secrète pour signer les jetons (à déplacer dans un fichier .env plus tard)
SECRET_KEY = "nexa_erp_secret_key_change_me_in_production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Le jeton sera valide 24 heures

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