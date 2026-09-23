from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean
from pydantic import BaseModel, EmailStr
from app.core.database import Base

# 1. TYPES D'ACTEURS (Définis par l'analyse fonctionnelle)

class UserType(str, Enum):
    SUPER_ADMIN = "super_admin"  # Profil 1 : Super Administrateur Plateforme SaaS
    ADMIN = "admin"              # Profil 2 : Administrateur Client (Admin Entreprise)
    STAFF = "staff"              # Profil 3 : Collaborateurs internes (Commercial, Magasinier, etc.)
    EXTERNAL = "external"        # Profil 4 : Utilisateurs Portail Externe (Clients / Fournisseurs)


# 2. MODÈLE ORM (SQLAlchemy)

class UserORM(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)  # Identifiant immuable de l'entreprise
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    user_type = Column(String, default=UserType.STAFF, nullable=False)  # Type d'acteur
    role_id = Column(Integer, nullable=True)               # Clé vers le rôle RBAC (Étape suivante)
    is_active = Column(Boolean, default=True)


# 3. SCHÉMAS PYDANTIC (Validation des entrées/sorties)

class UserCreate(BaseModel):
    tenant_id: str
    email: EmailStr
    password: str
    user_type: UserType = UserType.STAFF


class UserResponse(BaseModel):
    id: int
    tenant_id: str
    email: EmailStr
    user_type: UserType
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"