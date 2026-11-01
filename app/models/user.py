from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr
from app.core.database import Base


# 1. TYPES D'ACTEURS
class UserType(str, Enum):
    SUPER_ADMIN = "super_admin"  # Profil 1 : Super Administrateur Plateforme SaaS
    ADMIN = "admin"              # Profil 2 : Administrateur Client (Admin Entreprise)
    STAFF = "staff"              # Profil 3 : Collaborateurs internes (Commercial, Magasinier, etc.)
    EXTERNAL = "external"        # Profil 4 : Utilisateurs Portail Externe (Clients / Fournisseurs)


# 2. MODÈLE ORM (SQLAlchemy)
class UserORM(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    user_type = Column(String, default=UserType.STAFF, nullable=False)
    role_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)

    # Sécurité renforcée & 2FA / MFA
    two_factor_secret = Column(String, nullable=True)
    is_two_factor_enabled = Column(Boolean, default=False)
    backup_codes = Column(String, nullable=True)  # Codes de secours hachés ou séparés par virgules
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations de sessions et d'appareils
    sessions = relationship("UserSessionORM", back_populates="user", cascade="all, delete-orphan")
    devices = relationship("UserDeviceORM", back_populates="user", cascade="all, delete-orphan")


# 3. SCHÉMAS PYDANTIC
class UserCreate(BaseModel):
    tenant_id: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    user_type: UserType = UserType.STAFF


class UserResponse(BaseModel):
    id: int
    tenant_id: str
    email: EmailStr
    full_name: Optional[str] = None
    user_type: UserType
    is_active: bool
    is_two_factor_enabled: bool = False
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    requires_2fa: bool = False
    temp_token: Optional[str] = None  # Jeton temporaire utilisé pour valider le 2FA
