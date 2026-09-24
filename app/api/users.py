from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tenant import get_current_tenant_id
from app.core.rbac import RoleChecker
from app.models.user import UserORM
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users Management"])

# Seuls les administrateurs du tenant peuvent gérer les utilisateurs
allow_admin_only = RoleChecker(["admin", "super_admin"])


@router.get("/", response_model=List[UserResponse], dependencies=[Depends(allow_admin_only)])
def list_tenant_users(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Récupère la liste de tous les utilisateurs de l'entreprise (tenant) connectée.
    """
    users = db.query(UserORM).filter(UserORM.tenant_id == tenant_id).all()
    return users


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(allow_admin_only)])
def get_user_by_id(
    user_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Récupère les détails d'un utilisateur spécifique du tenant.
    """
    user = db.query(UserORM).filter(
        UserORM.id == user_id,
        UserORM.tenant_id == tenant_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable dans votre entreprise."
        )
    return user


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(allow_admin_only)])
def update_user_role(
    user_id: int,
    user_update: UserUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Met à jour le rôle ou le statut d'un utilisateur au sein du même tenant.
    """
    user = db.query(UserORM).filter(
        UserORM.id == user_id,
        UserORM.tenant_id == tenant_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable."
        )

    if user_update.user_type is not None:
        user.user_type = user_update.user_type
    if user_update.email is not None:
        user.email = user_update.email

    db.commit()
    db.refresh(user)
    return user