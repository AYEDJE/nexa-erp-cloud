from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import Base

# 1. MODÈLES ORM (SQLAlchemy)

class RoleORM(Base):
    """
    Rôles configurables par l'Admin Entreprise (ex: Responsable Commercial, Magasinier).
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)  # Isolation par entreprise
    name = Column(String, nullable=False)                   # Nom du rôle (ex: "Magasinier")
    description = Column(String, nullable=True)
    is_preconfigured = Column(Boolean, default=False)      # Indique si c'est un rôle modèle par défaut

    # Relation avec les permissions associées
    permissions = relationship("PermissionORM", back_populates="role", cascade="all, delete-orphan")


class PermissionORM(Base):
    """
    Permissions granulaires par module selon les 6 niveaux de l'analyse fonctionnelle.
    """
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    module_name = Column(String, nullable=False)           # Ex: "stock", "sales", "crm", "accounting"
    
    # Les 6 niveaux de permissions explicites
    can_read = Column(Boolean, default=False)       # 1. Consultation
    can_create = Column(Boolean, default=False)     # 2. Création
    can_update = Column(Boolean, default=False)     # 3. Modification
    can_delete = Column(Boolean, default=False)     # 4. Suppression
    can_validate = Column(Boolean, default=False)   # 5. Validation
    can_export = Column(Boolean, default=False)     # 6. Export

    role = relationship("RoleORM", back_populates="permissions")

# 2. SCHÉMAS PYDANTIC (Validation des API)

class PermissionSchema(BaseModel):
    module_name: str
    can_read: bool = False
    can_create: bool = False
    can_update: bool = False
    can_delete: bool = False
    can_validate: bool = False
    can_export: bool = False

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[PermissionSchema]


class RoleResponse(BaseModel):
    id: int
    tenant_id: str
    name: str
    description: Optional[str] = None
    is_preconfigured: bool
    permissions: List[PermissionSchema]

    class Config:
        from_attributes = True