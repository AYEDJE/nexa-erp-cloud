from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import RoleChecker, canonical_user_type
from app.models.activity import AccessLogORM, SecurityNotificationORM
from app.models.user import UserORM
from app.services.access_trace import ensure_policy

router = APIRouter(prefix="/security", tags=["Traçabilité et notifications"])
allow_member = RoleChecker(["staff", "admin", "super_admin"])


class ProfileIn(BaseModel):
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    notify_email: bool = True
    notify_sms: bool = True
    notify_whatsapp: bool = True
    notify_telegram: bool = True


class PolicyIn(BaseModel):
    email_enabled: bool = True
    sms_enabled: bool = True
    whatsapp_enabled: bool = True
    telegram_enabled: bool = True


def _tenant(current_user: dict) -> str:
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Entreprise absente du jeton.")
    return tenant_id


def _is_admin(current_user: dict) -> bool:
    return canonical_user_type(current_user.get("user_type")) in {"admin", "super_admin"}


def _user(db: Session, tenant_id: str, current_user: dict) -> UserORM:
    email = str(current_user.get("sub") or "").strip().lower()
    user = db.query(UserORM).filter(UserORM.email == email, UserORM.tenant_id == tenant_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable dans cette entreprise.")
    return user


def _log_row(row: AccessLogORM) -> dict:
    moment = row.occurred_at or datetime.utcnow()
    return {
        "id": row.id,
        "user_id": row.user_id,
        "email": row.email,
        "event_type": row.event_type,
        "date": moment.strftime("%d/%m/%Y"),
        "time": moment.strftime("%H:%M:%S"),
        "occurred_at": moment.isoformat(),
        "ip_address": row.ip_address,
        "method": row.method,
        "resource": row.resource,
        "detail": row.detail,
    }


@router.get("/overview")
def overview(db: Session = Depends(get_db), current_user: dict = Depends(allow_member)):
    tenant_id = _tenant(current_user)
    admin = _is_admin(current_user)
    me = _user(db, tenant_id, current_user)
    users = db.query(UserORM).filter(UserORM.tenant_id == tenant_id).order_by(UserORM.email).all()
    if not admin:
        users = [me]
    policy = ensure_policy(db, tenant_id)
    connection_query = db.query(AccessLogORM).filter(AccessLogORM.tenant_id == tenant_id, AccessLogORM.event_type.like("login_%"))
    notification_query = db.query(SecurityNotificationORM).filter(SecurityNotificationORM.tenant_id == tenant_id)
    if not admin:
        connection_query = connection_query.filter(AccessLogORM.user_id == me.id)
        notification_query = notification_query.filter(SecurityNotificationORM.user_id == me.id)
    db.commit()
    return {
        "company_scope": admin,
        "users": [_person(user) for user in users],
        "connections": connection_query.count(),
        "notifications": notification_query.count(),
        "policy": _policy(policy),
    }


@router.get("/connections")
def connections(db: Session = Depends(get_db), current_user: dict = Depends(allow_member)):
    tenant_id = _tenant(current_user)
    query = db.query(AccessLogORM).filter(AccessLogORM.tenant_id == tenant_id, AccessLogORM.event_type.like("login_%"))
    if not _is_admin(current_user):
        query = query.filter(AccessLogORM.user_id == _user(db, tenant_id, current_user).id)
    rows = query.order_by(AccessLogORM.id.desc()).limit(200).all()
    return [_log_row(row) for row in rows]


@router.get("/activities")
def activities(db: Session = Depends(get_db), current_user: dict = Depends(allow_member)):
    tenant_id = _tenant(current_user)
    query = db.query(AccessLogORM).filter(AccessLogORM.tenant_id == tenant_id)
    if not _is_admin(current_user):
        query = query.filter(AccessLogORM.user_id == _user(db, tenant_id, current_user).id)
    rows = query.order_by(AccessLogORM.id.desc()).limit(200).all()
    return [_log_row(row) for row in rows]


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), current_user: dict = Depends(allow_member)):
    tenant_id = _tenant(current_user)
    query = db.query(SecurityNotificationORM).filter(SecurityNotificationORM.tenant_id == tenant_id)
    if not _is_admin(current_user):
        query = query.filter(SecurityNotificationORM.user_id == _user(db, tenant_id, current_user).id)
    rows = query.order_by(SecurityNotificationORM.id.desc()).limit(200).all()
    return [{
        "id": row.id,
        "email": row.email,
        "channel": row.channel,
        "destination": row.destination,
        "status": row.status,
        "message": row.message,
        "provider_detail": row.provider_detail,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    } for row in rows]


@router.get("/profile")
def read_profile(db: Session = Depends(get_db), current_user: dict = Depends(allow_member)):
    user = _user(db, _tenant(current_user), current_user)
    return _profile(user)


@router.put("/profile")
def update_profile(body: ProfileIn, db: Session = Depends(get_db), current_user: dict = Depends(allow_member)):
    user = _user(db, _tenant(current_user), current_user)
    user.phone = (body.phone or "").strip() or None
    user.telegram_chat_id = (body.telegram_chat_id or "").strip() or None
    user.notify_email = body.notify_email
    user.notify_sms = body.notify_sms
    user.notify_whatsapp = body.notify_whatsapp
    user.notify_telegram = body.notify_telegram
    db.commit()
    return _profile(user)


@router.get("/policy")
def read_policy(db: Session = Depends(get_db), current_user: dict = Depends(allow_member)):
    policy = ensure_policy(db, _tenant(current_user))
    db.commit()
    return _policy(policy)


@router.put("/policy", dependencies=[Depends(RoleChecker(["admin", "super_admin"]))])
def update_policy(body: PolicyIn, db: Session = Depends(get_db), current_user: dict = Depends(RoleChecker(["admin", "super_admin"]))):
    policy = ensure_policy(db, _tenant(current_user))
    policy.email_enabled = body.email_enabled
    policy.sms_enabled = body.sms_enabled
    policy.whatsapp_enabled = body.whatsapp_enabled
    policy.telegram_enabled = body.telegram_enabled
    policy.updated_at = datetime.utcnow()
    db.commit()
    return _policy(policy)


def _person(user: UserORM) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "last_activity_at": user.last_activity_at.isoformat() if user.last_activity_at else None,
        "last_login_ip": user.last_login_ip,
    }


def _profile(user: UserORM) -> dict:
    return {
        "phone": user.phone,
        "telegram_chat_id": user.telegram_chat_id,
        "notify_email": user.notify_email is not False,
        "notify_sms": user.notify_sms is not False,
        "notify_whatsapp": user.notify_whatsapp is not False,
        "notify_telegram": user.notify_telegram is not False,
    }


def _policy(policy) -> dict:
    return {
        "email_enabled": bool(policy.email_enabled),
        "sms_enabled": bool(policy.sms_enabled),
        "whatsapp_enabled": bool(policy.whatsapp_enabled),
        "telegram_enabled": bool(policy.telegram_enabled),
    }
