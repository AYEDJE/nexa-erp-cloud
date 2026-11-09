import hashlib
import os
import secrets
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.database import get_db
from app.core.tenant import get_current_tenant_id
from app.core.tenant_db import get_tenant_sessionmaker, normalize_tenant_id
from app.core.rbac import get_current_user
from app.models.room import (
    RoomActivityORM,
    RoomFileORM,
    RoomInvitationORM,
    RoomMemberORM,
    RoomMessageORM,
    RoomORM,
)
from app.models.user import UserORM
from app.schemas.room import (
    AcceptInvitation,
    ActivityOut,
    FileOut,
    InvitationCreate,
    MemberOut,
    MemberRoleUpdate,
    MessageCreate,
    MessageOut,
    RoomCreate,
    RoomOut,
    RoomUpdate,
)
from app.services.room_realtime import room_connections
from app.services.room_service import (
    get_actor,
    get_membership,
    get_room,
    invitation_expiry,
    make_invitation_token,
    record_activity,
    require_manager,
    require_member,
)

router = APIRouter(prefix="/rooms", tags=["Room Live"])


def _user_id(user: dict) -> int:
    value = user.get("user_id")
    if not value:
        raise HTTPException(status_code=401, detail="Identifiant utilisateur absent du jeton.")
    return int(value)


def _file_root(tenant_id: str) -> Path:
    base = Path(os.getenv("ROOM_UPLOAD_DIR", "private_uploads/rooms"))
    return base / normalize_tenant_id(tenant_id)


@router.post("", response_model=RoomOut, status_code=201)
def create_room(
    body: RoomCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    room = RoomORM(
        tenant_id=tenant_id,
        name=body.name.strip(),
        description=body.description,
        created_by=actor.id,
    )
    db.add(room)
    db.flush()

    db.add(RoomMemberORM(
        tenant_id=tenant_id,
        room_id=room.id,
        user_id=actor.id,
        role="owner",
    ))
    record_activity(db, tenant_id, room.id, "room_created", actor.id, {"name": room.name})
    db.commit()
    db.refresh(room)
    return room


@router.get("", response_model=list[RoomOut])
def list_rooms(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    return (
        db.query(RoomORM)
        .join(RoomMemberORM, RoomMemberORM.room_id == RoomORM.id)
        .filter(
            RoomORM.tenant_id == tenant_id,
            RoomORM.is_archived.is_(False),
            RoomMemberORM.tenant_id == tenant_id,
            RoomMemberORM.user_id == actor.id,
        )
        .order_by(RoomORM.updated_at.desc())
        .all()
    )


@router.patch("/{room_id}", response_model=RoomOut)
def update_room(
    room_id: int,
    body: RoomUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    room, member = require_member(db, tenant_id, room_id, actor.id)
    require_manager(member)

    changes = body.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        room.name = changes["name"].strip()
    if "description" in changes:
        room.description = changes["description"]
    if changes.get("is_archived") is True:
        room.is_archived = True

    room.updated_at = datetime.utcnow()
    record_activity(db, tenant_id, room_id, "room_updated", actor.id, changes)
    db.commit()
    db.refresh(room)
    return room


@router.get("/{room_id}/members", response_model=list[MemberOut])
def list_members(
    room_id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    require_member(db, tenant_id, room_id, actor.id)

    rows = (
        db.query(RoomMemberORM, UserORM)
        .join(UserORM, UserORM.id == RoomMemberORM.user_id)
        .filter(
            RoomMemberORM.tenant_id == tenant_id,
            RoomMemberORM.room_id == room_id,
            UserORM.tenant_id == tenant_id,
        )
        .order_by(RoomMemberORM.joined_at.asc())
        .all()
    )
    return [
        {
            "id": member.id,
            "user_id": member.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "role": member.role,
            "joined_at": member.joined_at,
        }
        for member, user in rows
    ]


@router.post("/{room_id}/invitations", status_code=201)
def create_invitation(
    room_id: int,
    body: InvitationCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    _, member = require_member(db, tenant_id, room_id, actor.id)
    require_manager(member)

    email = str(body.email).strip().lower()
    invited_user = (
        db.query(UserORM)
        .filter(UserORM.tenant_id == tenant_id, UserORM.email == email, UserORM.is_active.is_(True))
        .first()
    )
    if not invited_user:
        raise HTTPException(
            status_code=404,
            detail="Cet utilisateur doit d’abord avoir un compte actif dans cette entreprise.",
        )

    existing = db.query(RoomMemberORM).filter_by(
        tenant_id=tenant_id, room_id=room_id, user_id=invited_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Cet utilisateur est déjà membre de l’espace.")

    raw_token, token_hash = make_invitation_token()
    invitation = RoomInvitationORM(
        tenant_id=tenant_id,
        room_id=room_id,
        email=email,
        token_hash=token_hash,
        role=body.role,
        invited_by=actor.id,
        expires_at=invitation_expiry(),
    )
    db.add(invitation)
    record_activity(db, tenant_id, room_id, "invitation_created", actor.id, {"email": email})
    db.commit()

    # Le jeton est retourné une seule fois. À transmettre au destinataire par un canal privé.
    return {
        "message": "Invitation créée. Transmettez ce jeton au destinataire.",
        "email": email,
        "role": body.role,
        "token": raw_token,
        "expires_at": invitation.expires_at.isoformat(),
    }


@router.post("/invitations/accept")
def accept_invitation(
    body: AcceptInvitation,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    token_hash = hashlib.sha256(body.token.encode("utf-8")).hexdigest()
    invitation = (
        db.query(RoomInvitationORM)
        .filter(
            RoomInvitationORM.tenant_id == tenant_id,
            RoomInvitationORM.token_hash == token_hash,
            RoomInvitationORM.accepted_at.is_(None),
        )
        .first()
    )
    if not invitation or invitation.expires_at < datetime.utcnow():
        raise HTTPException(status_code=404, detail="Invitation invalide ou expirée.")

    if actor.email.strip().lower() != invitation.email.strip().lower():
        raise HTTPException(status_code=403, detail="Cette invitation est destinée à un autre compte.")

    already_member = db.query(RoomMemberORM).filter_by(
        tenant_id=tenant_id, room_id=invitation.room_id, user_id=actor.id
    ).first()
    if already_member:
        invitation.accepted_at = datetime.utcnow()
        db.commit()
        return {"message": "Vous êtes déjà membre de cet espace."}

    invitation.accepted_at = datetime.utcnow()
    db.add(RoomMemberORM(
        tenant_id=tenant_id,
        room_id=invitation.room_id,
        user_id=actor.id,
        role=invitation.role,
    ))
    record_activity(
        db, tenant_id, invitation.room_id, "member_joined", actor.id,
        {"email": actor.email, "role": invitation.role},
    )
    db.commit()
    return {"message": "Invitation acceptée."}


@router.patch("/{room_id}/members/{member_id}")
def update_member_role(
    room_id: int,
    member_id: int,
    body: MemberRoleUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    _, actor_membership = require_member(db, tenant_id, room_id, actor.id)
    target = db.query(RoomMemberORM).filter_by(
        id=member_id, tenant_id=tenant_id, room_id=room_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Membre introuvable.")

    if actor_membership.role != "owner":
        raise HTTPException(status_code=403, detail="Seul le propriétaire peut modifier les rôles.")
    if target.role == "owner":
        raise HTTPException(status_code=400, detail="Le rôle du propriétaire ne peut pas être modifié.")

    target.role = body.role
    record_activity(db, tenant_id, room_id, "member_role_updated", actor.id, {
        "member_id": member_id,
        "role": body.role,
    })
    db.commit()
    return {"message": "Rôle mis à jour.", "role": target.role}


@router.delete("/{room_id}/members/{member_id}")
def remove_member(
    room_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    _, actor_membership = require_member(db, tenant_id, room_id, actor.id)
    require_manager(actor_membership)

    target = db.query(RoomMemberORM).filter_by(
        id=member_id, tenant_id=tenant_id, room_id=room_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Membre introuvable.")
    if target.role == "owner":
        raise HTTPException(status_code=400, detail="Le propriétaire ne peut pas être retiré.")
    if actor_membership.role != "owner" and target.role == "admin":
        raise HTTPException(status_code=403, detail="Seul le propriétaire peut retirer un administrateur.")

    db.delete(target)
    record_activity(db, tenant_id, room_id, "member_removed", actor.id, {"member_id": member_id})
    db.commit()
    return {"message": "Membre retiré de l’espace."}


@router.get("/{room_id}/messages", response_model=list[MessageOut])
def list_messages(
    room_id: int,
    before_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    require_member(db, tenant_id, room_id, actor.id)

    query = db.query(RoomMessageORM).filter_by(tenant_id=tenant_id, room_id=room_id)
    if before_id:
        query = query.filter(RoomMessageORM.id < before_id)
    return query.order_by(RoomMessageORM.id.desc()).limit(limit).all()[::-1]


@router.post("/{room_id}/messages", response_model=MessageOut, status_code=201)
async def send_message(
    room_id: int,
    body: MessageCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    _, member = require_member(db, tenant_id, room_id, actor.id)
    if member.role == "observer":
        raise HTTPException(status_code=403, detail="Un observateur ne peut pas envoyer de message.")

    message = RoomMessageORM(
        tenant_id=tenant_id,
        room_id=room_id,
        user_id=actor.id,
        content=body.content.strip(),
    )
    db.add(message)
    record_activity(db, tenant_id, room_id, "message_sent", actor.id)
    db.commit()
    db.refresh(message)

    await room_connections.broadcast(tenant_id, room_id, {
        "type": "message",
        "message": {
            "id": message.id,
            "room_id": message.room_id,
            "user_id": message.user_id,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        },
    })
    return message


@router.get("/{room_id}/files", response_model=list[FileOut])
def list_files(
    room_id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    require_member(db, tenant_id, room_id, actor.id)
    return (
        db.query(RoomFileORM)
        .filter_by(tenant_id=tenant_id, room_id=room_id)
        .order_by(RoomFileORM.id.desc())
        .limit(100)
        .all()
    )


MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".docx"}
MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("/{room_id}/files", response_model=FileOut, status_code=201)
async def upload_file(
    room_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    _, member = require_member(db, tenant_id, room_id, actor.id)
    if member.role == "observer":
        raise HTTPException(status_code=403, detail="Un observateur ne peut pas déposer de fichier.")

    original_name = (file.filename or "fichier").replace("\\", "/").split("/")[-1][:255]
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Format de fichier non accepté.")

    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Le fichier dépasse la limite de 10 Mo.")
    if not content:
        raise HTTPException(status_code=400, detail="Le fichier est vide.")

    storage_name = f"{uuid4().hex}{extension}"
    root = _file_root(tenant_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / storage_name).write_bytes(content)

    record = RoomFileORM(
        tenant_id=tenant_id,
        room_id=room_id,
        uploaded_by=actor.id,
        original_name=original_name,
        storage_name=storage_name,
        media_type=MEDIA_TYPES[extension],
        size_bytes=len(content),
    )
    db.add(record)
    record_activity(db, tenant_id, room_id, "file_uploaded", actor.id, {
        "filename": original_name,
        "size_bytes": len(content),
    })
    db.commit()
    db.refresh(record)
    return record


@router.get("/{room_id}/files/{file_id}/download")
def download_file(
    room_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    require_member(db, tenant_id, room_id, actor.id)
    record = db.query(RoomFileORM).filter_by(
        id=file_id, tenant_id=tenant_id, room_id=room_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Fichier introuvable.")

    path = _file_root(tenant_id) / record.storage_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier absent du stockage.")
    return FileResponse(
        path,
        media_type=record.media_type,
        filename=record.original_name,
    )


@router.get("/{room_id}/activities", response_model=list[ActivityOut])
def list_activities(
    room_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    actor = get_actor(db, current_user, tenant_id)
    require_member(db, tenant_id, room_id, actor.id)
    return (
        db.query(RoomActivityORM)
        .filter_by(tenant_id=tenant_id, room_id=room_id)
        .order_by(RoomActivityORM.id.desc())
        .limit(limit)
        .all()
    )


@router.websocket("/{room_id}/live")
async def room_live(websocket: WebSocket, room_id: int):
    # Le navigateur envoie son jeton comme premier message WebSocket,
    # plutôt que dans l'URL, où il pourrait être journalisé.
    await websocket.accept()
    db = None
    tenant_id = None
    user_id = None

    try:
        import asyncio

        first = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        token = first.get("token") if isinstance(first, dict) else None
        if not token:
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
        if not tenant_id or not user_id:
            await websocket.close(code=4401, reason="Identité invalide")
            return

        db = get_tenant_sessionmaker(tenant_id)()
        actor = (
            db.query(UserORM)
            .filter(
                UserORM.id == user_id,
                UserORM.tenant_id == tenant_id,
                UserORM.is_active.is_(True),
            )
            .first()
        )
        if not actor:
            await websocket.close(code=4401, reason="Compte invalide")
            return

        require_member(db, tenant_id, room_id, actor.id)
        count = await room_connections.connect(tenant_id, room_id, actor.id, websocket)

        await websocket.send_json({
            "type": "presence",
            "user_ids": await room_connections.presence(tenant_id, room_id),
        })
        await room_connections.broadcast(
            tenant_id, room_id,
            {"type": "presence", "user_ids": await room_connections.presence(tenant_id, room_id)},
            exclude=websocket,
        )

        while True:
            event = await websocket.receive_json()
            if isinstance(event, dict) and event.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif isinstance(event, dict) and event.get("type") == "typing":
                member = get_membership(db, tenant_id, room_id, actor.id)
                if member.role != "observer":
                    await room_connections.broadcast(
                        tenant_id,
                        room_id,
                        {"type": "typing", "user_id": actor.id},
                        exclude=websocket,
                    )

    except WebSocketDisconnect:
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
            count = await room_connections.disconnect(tenant_id, room_id, user_id, websocket)
            await room_connections.broadcast(
                tenant_id,
                room_id,
                {"type": "presence", "user_ids": await room_connections.presence(tenant_id, room_id)},
            )