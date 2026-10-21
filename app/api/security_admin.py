from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.tenant import get_current_tenant_id
from app.core.rbac import RoleChecker
from app.models.security import (
    UserDeviceORM,
    UserSessionORM,
    SecurityAlertORM,
    DeviceResponse,
    SecurityAlertResponse
)

router = APIRouter(prefix="/admin/security", tags=["Administration Sécurité & Appareils"])

allow_admin_only = RoleChecker(["admin", "super_admin"])


# --- 1. GESTION DES APPAREILS (CONSOLE ADMIN) ---

@router.get("/devices", response_model=List[DeviceResponse], dependencies=[Depends(allow_admin_only)])
def list_tenant_devices(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Console d'administration : Liste tous les appareils enregistrés au sein du tenant.
    """
    return db.query(UserDeviceORM).filter(UserDeviceORM.tenant_id == tenant_id).all()


@router.post("/devices/{device_id}/block", dependencies=[Depends(allow_admin_only)])
def block_device(
    device_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Bloque immédiatement un appareil suspect et révoque toutes ses sessions en cours.
    """
    device = db.query(UserDeviceORM).filter(
        UserDeviceORM.id == device_id,
        UserDeviceORM.tenant_id == tenant_id
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")

    device.status = "blocked"

    # Déconnexion à distance : Révocation de toutes les sessions associées à cet appareil
    db.query(UserSessionORM).filter(
        UserSessionORM.device_id == device.device_identifier,
        UserSessionORM.tenant_id == tenant_id
    ).update({"is_revoked": True})

    db.commit()
    return {"message": f"Appareil '{device.device_name}' bloqué et sessions distantes révoquées."}


@router.post("/devices/{device_id}/unblock", dependencies=[Depends(allow_admin_only)])
def unblock_device(
    device_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Réactive un appareil précédemment bloqué.
    """
    device = db.query(UserDeviceORM).filter(
        UserDeviceORM.id == device_id,
        UserDeviceORM.tenant_id == tenant_id
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")

    device.status = "authorized"
    db.commit()
    return {"message": f"Appareil '{device.device_name}' réautorisé avec succès."}


@router.post("/devices/{device_id}/disconnect", dependencies=[Depends(allow_admin_only)])
def remote_disconnect_device(
    device_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Déconnexion forcée à distance de toutes les sessions sur cet appareil.
    """
    device = db.query(UserDeviceORM).filter(
        UserDeviceORM.id == device_id,
        UserDeviceORM.tenant_id == tenant_id
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")

    revoked_count = db.query(UserSessionORM).filter(
        UserSessionORM.device_id == device.device_identifier,
        UserSessionORM.tenant_id == tenant_id,
        UserSessionORM.is_revoked == False
    ).update({"is_revoked": True})

    db.commit()
    return {"message": f"{revoked_count} session(s) active(s) déconnectée(s) à distance sur cet appareil."}


@router.delete("/devices/{device_id}", dependencies=[Depends(allow_admin_only)])
def delete_device(
    device_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Supprime un appareil enregistré et révoque ses sessions.
    """
    device = db.query(UserDeviceORM).filter(
        UserDeviceORM.id == device_id,
        UserDeviceORM.tenant_id == tenant_id
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")

    db.query(UserSessionORM).filter(
        UserSessionORM.device_id == device.device_identifier,
        UserSessionORM.tenant_id == tenant_id
    ).update({"is_revoked": True})

    db.delete(device)
    db.commit()
    return {"message": f"Appareil supprimé du parc de l'entreprise."}


# --- 2. GESTION DES ÉVÉNEMENTS & ALERTES DE SÉCURITÉ ---

@router.get("/alerts", response_model=List[SecurityAlertResponse], dependencies=[Depends(allow_admin_only)])
def list_security_alerts(
    tenant_id: str = Depends(get_current_tenant_id),
    resolved: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Consulte le journal des alertes de sécurité pour le tenant (brute-force, connexions suspectes, etc.).
    """
    query = db.query(SecurityAlertORM).filter(SecurityAlertORM.tenant_id == tenant_id)
    if resolved is not None:
        query = query.filter(SecurityAlertORM.is_resolved == resolved)

    return query.order_by(SecurityAlertORM.created_at.desc()).all()


@router.post("/alerts/{alert_id}/resolve", dependencies=[Depends(allow_admin_only)])
def resolve_security_alert(
    alert_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    alert = db.query(SecurityAlertORM).filter(
        SecurityAlertORM.id == alert_id,
        SecurityAlertORM.tenant_id == tenant_id
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alerte introuvable.")

    alert.is_resolved = True
    db.commit()
    return {"message": "Alerte marquée comme résolue."}
