import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.database import get_db
from app.core.rbac import get_current_user
from app.core.tenant import get_current_tenant_id
from app.core.tenant_db import get_tenant_sessionmaker
from app.models.meeting import MeetingMemberORM, MeetingORM
from app.models.user import UserORM
from app.services.meeting_realtime import meeting_connections

router = APIRouter(prefix="/meetings", tags=["Room Live - Réunions vidéo"])
MAX_SIGNAL_BYTES = 64 * 1024


class MeetingCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)


class MemberAdd(BaseModel):
    email: str = Field(min_length=3, max_length=255)


def _actor(db: Session, current_user: dict, tenant_id: str) -> UserORM:
    actor = db.query(UserORM).filter(
        UserORM.id == current_user.get("user_id"),
        UserORM.tenant_id == tenant_id,
        UserORM.is_active.is_(True),
    ).first()
    if not actor:
        raise HTTPException(status_code=401, detail="Compte utilisateur introuvable ou inactif.")
    return actor


def _meeting_for_member(db: Session, tenant_id: str, meeting_id: int, user_id: int) -> MeetingORM:
    meeting = db.query(MeetingORM).filter_by(id=meeting_id, tenant_id=tenant_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Réunion introuvable.")
    if meeting.is_closed:
        raise HTTPException(status_code=410, detail="Cette réunion est terminée.")
    member = db.query(MeetingMemberORM).filter_by(
        tenant_id=tenant_id, meeting_id=meeting_id, user_id=user_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas invité à cette réunion.")
    return meeting


@router.post("", status_code=201)
def create_meeting(
    body: MeetingCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = _actor(db, current_user, tenant_id)
    meeting = MeetingORM(tenant_id=tenant_id, title=body.title.strip(), created_by=actor.id)
    db.add(meeting)
    db.flush()
    db.add(MeetingMemberORM(tenant_id=tenant_id, meeting_id=meeting.id, user_id=actor.id))
    db.commit()
    db.refresh(meeting)
    return {"id": meeting.id, "title": meeting.title, "created_by": meeting.created_by, "created_at": meeting.created_at}


@router.get("")
def list_meetings(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = _actor(db, current_user, tenant_id)
    rows = db.query(MeetingORM).join(
        MeetingMemberORM, MeetingMemberORM.meeting_id == MeetingORM.id
    ).filter(
        MeetingORM.tenant_id == tenant_id,
        MeetingMemberORM.tenant_id == tenant_id,
        MeetingMemberORM.user_id == actor.id,
    ).order_by(MeetingORM.created_at.desc()).limit(100).all()
    return [{"id": row.id, "title": row.title, "created_by": row.created_by,
             "is_closed": row.is_closed, "created_at": row.created_at} for row in rows]


@router.post("/{meeting_id}/members", status_code=201)
def add_meeting_member(
    meeting_id: int,
    body: MemberAdd,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = _actor(db, current_user, tenant_id)
    meeting = _meeting_for_member(db, tenant_id, meeting_id, actor.id)
    if meeting.created_by != actor.id:
        raise HTTPException(status_code=403, detail="Seul le créateur peut inviter des participants.")
    email = body.email.strip().lower()
    invited = db.query(UserORM).filter(
        UserORM.tenant_id == tenant_id,
        UserORM.email == email,
        UserORM.is_active.is_(True),
    ).first()
    if not invited:
        raise HTTPException(status_code=404, detail="Aucun compte actif de cette entreprise ne correspond à cet e-mail.")
    existing = db.query(MeetingMemberORM).filter_by(
        tenant_id=tenant_id, meeting_id=meeting_id, user_id=invited.id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Cet utilisateur participe déjà à la réunion.")
    db.add(MeetingMemberORM(tenant_id=tenant_id, meeting_id=meeting_id, user_id=invited.id))
    db.commit()
    return {"message": "Participant ajouté.", "email": invited.email}


@router.post("/{meeting_id}/close")
def close_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = _actor(db, current_user, tenant_id)
    meeting = _meeting_for_member(db, tenant_id, meeting_id, actor.id)
    if meeting.created_by != actor.id:
        raise HTTPException(status_code=403, detail="Seul le créateur peut terminer la réunion.")
    from datetime import datetime
    meeting.is_closed = True
    meeting.closed_at = datetime.utcnow()
    db.commit()
    return {"message": "Réunion terminée."}


@router.websocket("/{meeting_id}/live")
async def meeting_signal(websocket: WebSocket, meeting_id: int):
    # Authentifier via le premier message au lieu de placer le JWT dans l'URL.
    await websocket.accept()
    db = None
    tenant_id = None
    user_id = None
    try:
        auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        token = auth_message.get("token") if isinstance(auth_message, dict) else None
        if not isinstance(token, str) or not token:
            await websocket.close(code=4401, reason="Jeton requis")
            return
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("token_type") not in (None, "access"):
            await websocket.close(code=4401, reason="Jeton d'accès requis")
            return
        from app.services.session_guard import assert_active_session
        assert_active_session(payload)

        tenant_id = payload.get("tenant_id")
        user_id = int(payload.get("user_id") or 0)
        if not tenant_id or user_id < 1:
            await websocket.close(code=4401, reason="Identité invalide")
            return
        db = get_tenant_sessionmaker(tenant_id)()
        actor = db.query(UserORM).filter(
            UserORM.id == user_id,
            UserORM.tenant_id == tenant_id,
            UserORM.is_active.is_(True),
        ).first()
        if not actor:
            await websocket.close(code=4401, reason="Compte invalide")
            return
        _meeting_for_member(db, tenant_id, meeting_id, user_id)

        existing_ids = await meeting_connections.join(tenant_id, meeting_id, user_id, websocket)
        await websocket.send_json({"type": "participants", "user_ids": existing_ids})
        await meeting_connections.broadcast(
            tenant_id, meeting_id,
            {"type": "participant_joined", "user_id": user_id},
            exclude_user_id=user_id,
        )

        while True:
            message = await websocket.receive_json()
            if not isinstance(message, dict):
                continue
            kind = message.get("type")
            if kind == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if kind not in {"offer", "answer", "ice-candidate"}:
                continue
            recipient = message.get("to_user_id")
            data = message.get("data")
            if not isinstance(recipient, int) or not isinstance(data, dict):
                continue
            if len(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")) > MAX_SIGNAL_BYTES:
                await websocket.send_json({"type": "error", "message": "Message de signalisation trop volumineux."})
                continue
            _meeting_for_member(db, tenant_id, meeting_id, user_id)
            delivered = await meeting_connections.send_to_user(
                tenant_id, meeting_id, recipient,
                {"type": kind, "from_user_id": user_id, "data": data},
            )
            if not delivered:
                await websocket.send_json({"type": "peer_unavailable", "user_id": recipient})

    except WebSocketDisconnect:
        pass
    except (JWTError, ValueError, TypeError):
        try:
            await websocket.close(code=4401, reason="Jeton invalide")
        except Exception:
            pass
    except Exception:
        try:
            await websocket.close(code=4403, reason="Connexion refusée")
        except Exception:
            pass
    finally:
        if db is not None:
            db.close()
        if tenant_id and user_id:
            remaining = await meeting_connections.leave(tenant_id, meeting_id, user_id, websocket)
            await meeting_connections.broadcast(
                tenant_id, meeting_id,
                {"type": "participant_left", "user_id": user_id, "user_ids": remaining},
            )
