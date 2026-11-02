from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tenant import get_current_tenant_id
from app.core.rbac import RoleChecker
from app.core.security import get_password_hash
from app.models.rbac import RoleORM
from app.models.user import UserORM
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users Management"])

# Seuls les administrateurs du tenant peuvent gérer les utilisateurs
allow_admin_only = RoleChecker(["admin", "super_admin"])

# Rôles proposés dans le formulaire : clé -> (nom du rôle, user_type)
ROLE_CATALOG = {
    "commercial":   ("Responsable Commercial", "staff"),
    "finance":      ("Responsable Financier et Comptable", "staff"),
    "stock":        ("Responsable des Stocks et Magasinier", "staff"),
    "achats":       ("Responsable des Achats", "staff"),
    "staff":        ("Collaborateur Standard", "staff"),
    "admin":        ("Administrateur Adjoint", "admin"),
    "client_ext":   ("Client Partenaire", "external"),
    "supplier_ext": ("Fournisseur Agréé", "external"),
}
ALLOWED_USER_TYPES = {"staff", "admin", "external"}


class UserCreateByAdmin(BaseModel):
    """Création par l'admin : le tenant vient du token, jamais du client."""
    full_name: Optional[str] = Field(default=None, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8)
    user_type: Optional[str] = None
    role: Optional[str] = None


def _role_names(db: Session, tenant_id: str) -> dict:
    return {r.id: r.name for r in db.query(RoleORM).filter(RoleORM.tenant_id == tenant_id).all()}


def _to_response(user: UserORM, role_names: dict) -> dict:
    return {
        "id": user.id,
        "tenant_id": user.tenant_id,
        "email": user.email,
        "full_name": user.full_name,
        "user_type": str(getattr(user.user_type, "value", user.user_type)),
        "role_id": user.role_id,
        "role_name": role_names.get(user.role_id),
        "is_active": True if user.is_active is None else user.is_active,
        "is_two_factor_enabled": bool(user.is_two_factor_enabled),
        "last_login_at": user.last_login_at,
    }


@router.get("/", response_model=List[UserResponse], dependencies=[Depends(allow_admin_only)])
def list_tenant_users(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Liste tous les utilisateurs de l'entreprise (tenant) connectée."""
    users = db.query(UserORM).filter(UserORM.tenant_id == tenant_id).order_by(UserORM.id).all()
    names = _role_names(db, tenant_id)
    return [_to_response(u, names) for u in users]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(allow_admin_only)])
def create_tenant_user(
    data: UserCreateByAdmin,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Crée un utilisateur dans l'entreprise de l'admin connecté."""
    if db.query(UserORM).filter(UserORM.email == data.email).first():
        raise HTTPException(status_code=400, detail="Un utilisateur avec cet e-mail existe déjà.")

    role_label, user_type = (None, data.user_type or "staff")
    if data.role:
        if data.role not in ROLE_CATALOG:
            raise HTTPException(status_code=422, detail=f"Rôle inconnu : {data.role}")
        role_label, user_type = ROLE_CATALOG[data.role]

    if user_type not in ALLOWED_USER_TYPES:
        raise HTTPException(status_code=422, detail="user_type doit être staff, admin ou external.")

    role_id = None
    if role_label:
        role = db.query(RoleORM).filter(RoleORM.tenant_id == tenant_id, RoleORM.name == role_label).first()
        if not role:
            role = RoleORM(tenant_id=tenant_id, name=role_label, is_preconfigured=True)
            db.add(role)
            db.flush()
        role_id = role.id

    user = UserORM(
        tenant_id=tenant_id,
        email=data.email,
        full_name=(data.full_name or "").strip() or None,
        hashed_password=get_password_hash(data.password),
        user_type=user_type,
        role_id=role_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_response(user, _role_names(db, tenant_id))


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(allow_admin_only)])
def get_user_by_id(
    user_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    user = db.query(UserORM).filter(UserORM.id == user_id, UserORM.tenant_id == tenant_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable dans votre entreprise.")
    return _to_response(user, _role_names(db, tenant_id))


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(allow_admin_only),
    db: Session = Depends(get_db),
):
    """Met à jour le nom, le type, l'email ou le statut (actif/désactivé)."""
    user = db.query(UserORM).filter(UserORM.id == user_id, UserORM.tenant_id == tenant_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    if user_update.is_active is not None:
        if user.id == current_user.get("user_id") and user_update.is_active is False:
            raise HTTPException(status_code=400, detail="Vous ne pouvez pas désactiver votre propre compte.")
        user.is_active = user_update.is_active

    if user_update.full_name is not None:
        user.full_name = user_update.full_name.strip() or None

    if user_update.user_type is not None:
        if user_update.user_type not in ALLOWED_USER_TYPES:
            raise HTTPException(status_code=422, detail="user_type doit être staff, admin ou external.")
        user.user_type = user_update.user_type

    if user_update.email is not None:
        user.email = user_update.email

    db.commit()
    db.refresh(user)
    return _to_response(user, _role_names(db, tenant_id))