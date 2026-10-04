from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_tenant_id  # Récupère l'ID du tenant connecté
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import get_tenant_audit_logs

router = APIRouter(prefix="/audit", tags=["Audit Logs"])

@router.get("/logs", response_model=List[AuditLogResponse])
def read_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Récupère les journaux d'audit du tenant actuel.
    L'isolation est garantie par le header X-Tenant-ID.
    """
    logs = get_tenant_audit_logs(db=db, tenant_id=tenant_id, skip=skip, limit=limit)
    return logs