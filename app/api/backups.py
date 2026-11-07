from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.tenant import get_current_tenant_id
from app.core.rbac import RoleChecker
from app.services.backup_service import (
    create_tenant_backup_snapshot,
    restore_tenant_from_snapshot
)

router = APIRouter(prefix="/admin/backups", tags=["Sauvegardes & Restauration"])

allow_admin_only = RoleChecker(["admin", "super_admin"])


class RestoreRequest(BaseModel):
    snapshot: Dict[str, Any]


@router.post("/export", dependencies=[Depends(allow_admin_only)])
def export_backup(
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(allow_admin_only),
    db: Session = Depends(get_db)
):
    """
    Exporte une sauvegarde complète des données du tenant (JSON snapshot chiffrable).
    """
    snapshot = create_tenant_backup_snapshot(tenant_id=tenant_id, db=db, user_id=current_user.get("user_id"))
    return snapshot


@router.post("/restore", dependencies=[Depends(allow_admin_only)])
def restore_backup(
    request: RestoreRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(allow_admin_only),
    db: Session = Depends(get_db)
):
    """
    Restaure les données du tenant depuis un instantané avec validation d'intégrité.
    """
    try:
        result = restore_tenant_from_snapshot(
            snapshot=request.snapshot,
            target_tenant_id=tenant_id,
            db=db,
            user_id=current_user.get("user_id"),
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Échec de la restauration : {str(e)}"
        )
