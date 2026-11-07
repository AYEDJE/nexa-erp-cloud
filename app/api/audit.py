from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import RoleChecker
from app.core.tenant import get_current_tenant_id
from app.models.audit import AuditLogORM
from app.models.user import UserORM

router = APIRouter(prefix="/audit", tags=["Audit Logs"])
allow_admin = RoleChecker(["admin", "super_admin"])


@router.get("/logs", dependencies=[Depends(allow_admin)])
def read_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Journal des opérations de l'entreprise connectée. Un autre espace n'y a pas accès."""
    rows = db.query(AuditLogORM).filter(AuditLogORM.tenant_id == tenant_id).order_by(AuditLogORM.id.desc()).offset(skip).limit(limit).all()
    emails = {user.id: user.email for user in db.query(UserORM).filter(UserORM.tenant_id == tenant_id).all()}
    result = []
    for row in rows:
        moment = row.created_at
        result.append({
            "id": row.id,
            "user_id": row.user_id,
            "email": emails.get(row.user_id),
            "action": row.action,
            "resource": row.resource,
            "details": row.details,
            "date": moment.strftime("%d/%m/%Y") if moment else None,
            "time": moment.strftime("%H:%M:%S") if moment else None,
            "created_at": moment.isoformat() if moment else None,
        })
    return result
