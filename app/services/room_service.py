import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.room import (
    RoomActivityORM,
    RoomMemberORM,
    RoomORM,
)
from app.models.user import UserORM


def get_actor(db: Session, current_user: dict, tenant_id: str) -> UserORM:
    user_id = current_user.get("user_id")
    user = (
        db.query(UserORM)
        .filter(
            UserORM.id == user_id,
            UserORM.tenant_id == tenant_id,
            UserORM.is_active.is_(True),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="Compte utilisateur introuvable ou inactif.")
    return user


def get_room(db: Session, tenant_id: str, room_id: int) -> RoomORM:
    room = (
        db.query(RoomORM)
        .filter(
            RoomORM.id == room_id,
            RoomORM.tenant_id == tenant_id,
            RoomORM.is_archived.is_(False),
        )
        .first()
    )
    if not room:
        raise HTTPException(status_code=404, detail="Espace introuvable.")
    return room


def get_membership(
    db: Session,
    tenant_id: str,
    room_id: int,
    user_id: int,
) -> RoomMemberORM:
    member = (
        db.query(RoomMemberORM)
        .filter_by(tenant_id=tenant_id, room_id=room_id, user_id=user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Vous ne faites pas partie de cet espace.")
    return member


def require_member(
    db: Session,
    tenant_id: str,
    room_id: int,
    user_id: int,
) -> tuple[RoomORM, RoomMemberORM]:
    room = get_room(db, tenant_id, room_id)
    member = get_membership(db, tenant_id, room_id, user_id)
    return room, member


def require_manager(member: RoomMemberORM) -> None:
    if member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Le rôle de cet espace ne permet pas cette action.")


def record_activity(
    db: Session,
    tenant_id: str,
    room_id: int,
    kind: str,
    user_id: Optional[int],
    details: Optional[dict] = None,
) -> RoomActivityORM:
    activity = RoomActivityORM(
        tenant_id=tenant_id,
        room_id=room_id,
        user_id=user_id,
        kind=kind,
        details=details or {},
    )
    db.add(activity)
    return activity


def make_invitation_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, token_hash


def invitation_expiry() -> datetime:
    return datetime.utcnow() + timedelta(days=7)