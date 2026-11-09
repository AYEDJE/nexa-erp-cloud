from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from app.core.database import Base


class RoomORM(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(String(1000), nullable=True)
    created_by = Column(Integer, nullable=False)
    is_archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class RoomMemberORM(Base):
    __tablename__ = "room_members"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_room_member_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(String(20), nullable=False, default="member")
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class RoomInvitationORM(Base):
    __tablename__ = "room_invitations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    role = Column(String(20), nullable=False, default="member")
    invited_by = Column(Integer, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class RoomMessageORM(Base):
    __tablename__ = "room_messages"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class RoomFileORM(Base):
    __tablename__ = "room_files"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)
    uploaded_by = Column(Integer, nullable=False)
    original_name = Column(String(255), nullable=False)
    storage_name = Column(String(100), nullable=False, unique=True)
    media_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class RoomActivityORM(Base):
    __tablename__ = "room_activities"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    kind = Column(String(50), nullable=False)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)