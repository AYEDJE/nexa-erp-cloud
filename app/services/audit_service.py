from sqlalchemy.orm import Session
from app.models.audit import AuditLogORM
from app.schemas.audit import AuditLogCreate
from typing import Optional, Dict, Any

def log_action(
    db: Session,
    tenant_id: str,
    action: str,
    resource: str,
    user_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None
) -> AuditLogORM:
    """
    Enregistre une entrée d'audit dans la BDD pour un tenant donné.
    """
    audit_entry = AuditLogORM(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource=resource,
        details=details
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry

def get_tenant_audit_logs(
    db: Session,
    tenant_id: str,
    skip: int = 0,
    limit: int = 50
):
    """
    Récupère les logs d'audit filtrés exclusivement par tenant (isolation multi-tenant).
    """
    return db.query(AuditLogORM)\
             .filter(AuditLogORM.tenant_id == tenant_id)\
             .order_by(AuditLogORM.created_at.desc())\
             .offset(skip)\
             .limit(limit)\
             .all()