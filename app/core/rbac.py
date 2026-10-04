from typing import List
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from app.core.config import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


class RoleChecker:
    """
    Dépendance FastAPI pour restreindre l'accès à une route
    selon les types d'utilisateurs autorisés.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, token: str = Depends(oauth2_scheme)) -> dict:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impossible de valider les identifiants de session.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_type: str = payload.get("user_type")

            if user_type is None:
                raise credentials_exception

            # Vérification du rôle contenu dans le token
            if user_type not in self.allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permissions insuffisantes pour accéder à cette ressource."
                )

            return payload

        except JWTError:
            raise credentials_exception